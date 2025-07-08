import json, time, os, argparse

from concurrent.futures import ThreadPoolExecutor

import with_selenium
from tqdm import tqdm
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains


class BuscaAdvogados:
    def _esperar_pagina_carregar(driver):
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return True
    
    def acessar_esaj():        
        chrome_options = webdriver.ChromeOptions()
        
        """Sem visuzalizacao do chrome"""
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--disable-dev-shm-usage")

        """Local de download especifico"""
        # nome_pasta = 'pdf/'+incidente['incidente']     
        # os.makedirs(nome_pasta, exist_ok=True)        
        # download_directory = os.path.join(os.getcwd(), 'pdf',incidente['incidente'])
        # prefs = {
        #     'download.default_directory': download_directory,
        #     'download.prompt_for_download': False,
        #     'download.directory_upgrade': True,
        #     'safebrowsing.enabled': True
        # }
        # chrome_options.add_experimental_option('prefs', prefs)

        service = Service()
        driver = webdriver.Chrome(service=service,options=chrome_options)

        driver.get('https://esaj.tjsp.jus.br/cpopg/open.do')
        BuscaAdvogados._esperar_pagina_carregar(driver)

        return driver
    
    def buscar_advogado(driver,nome_advogado:str):
        select_tipo_pesquisa = driver.find_element(By.CSS_SELECTOR,'select#cbPesquisa')
        select = Select(select_tipo_pesquisa)       
        select.select_by_value("NMADVOGADO")

        input_nome = driver.find_element(By.CSS_SELECTOR, 'input#campo_NMADVOGADO')
        input_nome.send_keys(nome_advogado)
        print('Inputado nome')
        time.sleep(5)

        btn_consultar = driver.find_element(By.CSS_SELECTOR,'input#botaoConsultarProcessos')
        btn_consultar.click()
        BuscaAdvogados._esperar_pagina_carregar(driver)
        
        return driver
    
    def retirar_info_processo(processo_element):   
        print('::::::::::::::::::::::::::::::::::::::::::::::::::::::::::')     
        resumo_processo = {}
        div_mae = processo_element                    
        id_processo = div_mae.get_attribute('id').replace('divProcesso','')
        resumo_processo['id_processo'] = id_processo
        print('ID do processo:',id_processo)

        div_colunas = div_mae.find_element(By.CSS_SELECTOR,'div.home__lista-de-processos')
        # print('Achei a div colunas?','sim' if div_colunas else 'nao')
        div_processo = div_colunas.find_element(By.CSS_SELECTOR,'div.nuProcesso')
        link_processo = div_processo.find_element(By.CSS_SELECTOR,'a')
        numero_processo = link_processo.text
        resumo_processo['numero_proceso'] = numero_processo
        link_processo = link_processo.get_attribute('href')
        resumo_processo['link_processo'] = link_processo

        classe_processo = div_colunas.find_element(By.CSS_SELECTOR,'div.classeProcesso').text
        assunto_processo = div_colunas.find_element(By.CSS_SELECTOR,'div.assuntoPrincipalProcesso').text
        data_distribuicao = div_colunas.find_element(By.CSS_SELECTOR,'div.dataLocalDistribuicaoProcesso').text

        resumo_processo['classe_processo'] = classe_processo
        resumo_processo['assunto_processo'] = assunto_processo
        resumo_processo['data_distruibuicao'] = data_distribuicao
        
        incidente_tag = f"a#incidentesRecursos_{id_processo}"
        try:
            link_incidentes_recursos = div_mae.find_element(By.CSS_SELECTOR,incidente_tag)
        except with_selenium.common.exceptions.NoSuchElementException:
            link_incidentes_recursos = None
        print('Achei o link para incidentes e recursos?', 'sim' if link_incidentes_recursos else 'nao')            
        resumo_processo['incidentes_recursos'] = 'possui' if link_incidentes_recursos else 'nao possui'
        resumo_processo['link_filhos'] = link_incidentes_recursos
        resumo_processo['incidente_ou_recurso'] = 'nao'

        return resumo_processo

    def buscar_processos(driver:webdriver):
        container_processos = driver.find_element(By.CSS_SELECTOR,'div#listagemDeProcessos')
        lista_processos = container_processos.find_element(By.CSS_SELECTOR,'ul')
        lista_processos =lista_processos.find_elements(By.CSS_SELECTOR,'li')
        print('Encontrados',len(lista_processos),'processos.')
        count = 1

        resultado = []
        for processo in lista_processos:   
            actions = ActionChains(driver)
            actions.move_to_element(processo).perform()
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", processo)         

            div_mae = processo.find_element(By.CSS_SELECTOR,'div')
            resumo_processo = BuscaAdvogados.retirar_info_processo(div_mae)
            resultado.append(resumo_processo)
            link_incidentes_recursos = resumo_processo.get('link_filhos',None)
            id_processo = resumo_processo.get('id_processo',None)

            if link_incidentes_recursos:
                time.sleep(3)
                link_incidentes_recursos.click()
                time.sleep(3)

                tag_div_filhos = f'div#divFilhos{id_processo}'
                div_filhos = driver.find_element(By.CSS_SELECTOR,tag_div_filhos)
                "div[contains(@id,'divProcesso')]"
                qtd_filhos = div_filhos.find_elements(By.CSS_SELECTOR,"div")
                print('Achei quantos filhos?',len(qtd_filhos))

                if len(qtd_filhos) == 0:
                    time.sleep(3)
                    link_incidentes_recursos.click()
                    time.sleep(3)
                    qtd_filhos = div_filhos.find_elements(By.CSS_SELECTOR,"div")

                for filho in qtd_filhos:
                    tipo_de_filho = filho.get_attribute('id')
                    if 'divProcesso' in tipo_de_filho:
                        resumo_filho = BuscaAdvogados.retirar_info_processo(filho)
                        resumo_filho['incidente_ou_recurso'] = 'sim'
                        resultado.append(resumo_filho)
            # print('Esse é o processo filho?',qtd_filhos if qtd_filhos.get_attribute('id') is not None else 'Nao')

            
            # df = pd.DataFrame(resultado)
            # df.to_excel('resultado.xlsx',index=False,engine='openpyxl')

            # resultado.append(resumo_processo)
            count += 1
            
        df = pd.DataFrame(resultado)
        df.to_excel('resultado.xlsx',index=False,engine='openpyxl')

    def inserir_processo(driver:webdriver):
        input_processo = driver.find_element(By.CSS_SELECTOR,'label#cbPesquisa')
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Busca processos no ESAJ")
    parser.add_argument('--process_num', type=str, default='', help='Número do processo a ser consultado.')
    args = parser.parse_args()
    
    driver = BuscaAdvogados.acessar_esaj()
    BuscaAdvogados.buscar_advogado(driver,'')
    BuscaAdvogados.buscar_processos(driver)
    print('Acabou.')