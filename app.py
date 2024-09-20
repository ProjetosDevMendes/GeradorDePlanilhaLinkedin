from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook
from time import sleep
import os
import platform
import subprocess
from webdriver_manager.chrome import ChromeDriverManager  # Importar o webdriver_manager

def read_credentials(file_path):
    credentials = {}
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.strip().split(":")
                credentials[key] = value
    except FileNotFoundError:
        print(f"Erro: arquivo {file_path} não encontrado.")
    except Exception as e:
        print(f"Erro ao ler o arquivo de credenciais: {e}")
    return credentials

def login(browser, credentials):
    try:
        print("Iniciando login no LinkedIn...")
        browser.get("https://www.linkedin.com/login")
        
        # Espera os campos de login aparecerem
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.ID, "username")))
        
        email = browser.find_element(By.ID, "username")
        password = browser.find_element(By.ID, "password")
        btn_entrar = browser.find_element(By.XPATH, "//button[contains(@class, 'btn__primary')]")
        
        email.send_keys(credentials['user'])
        password.send_keys(credentials['senha'])
        btn_entrar.click()
        
        print("Resolva o captcha no navegador...")
        input("Resolva o captcha no navegador e pressione ENTER aqui para continuar...")  # Aguarda o usuário resolver o captcha
        
        # Verifica se o login foi bem-sucedido
        WebDriverWait(browser, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__me"))
        )
        print("Login realizado com sucesso.")
    except TimeoutException:
        print("Erro: Timeout ao tentar realizar o login. Verifique se o LinkedIn está acessível ou se os IDs dos campos mudaram.")
    except NoSuchElementException:
        print("Erro: Elemento não encontrado durante o login. Verifique a estrutura do site.")
    except Exception as e:
        print(f"Erro durante o login: {e}")
        browser.quit()

def buscar_vagas(browser, search_term):
    try:
        print(f"Buscando vagas para '{search_term}'...")
        browser.get("https://www.linkedin.com/jobs/")
        
        # Espera o campo de busca de vagas aparecer
        WebDriverWait(browser, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.jobs-search-box__text-input"))
        )
        
        input_jobs_search = browser.find_element(By.CSS_SELECTOR, "input.jobs-search-box__text-input")
        input_jobs_search.send_keys(search_term)
        input_jobs_search.send_keys(Keys.ENTER)
        
        # Espera os resultados aparecerem
        WebDriverWait(browser, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-search-results-list"))
        )
        return browser.find_element(By.CSS_SELECTOR, "div.jobs-search-results-list")
    except TimeoutException:
        print("Erro: Timeout ao buscar as vagas. Verifique a conexão.")
    except Exception as e:
        print(f"Erro durante a busca de vagas: {e}")
        browser.quit()

def coletar_links(browser, ul_element, max_links=25):
    links = []
    try:
        while len(links) < max_links:
            print(f"Coletando links... Total coletado até agora: {len(links)}")
            
            # Scroll na lista de resultados de vagas
            browser.execute_script("arguments[0].scrollTop += 200;", ul_element)
            sleep(2)
            
            new_links = browser.find_elements(By.XPATH, "//main//div/div//ul//li//a[@data-control-id]")
            links += [link for link in new_links if link not in links]  # Adiciona somente novos links
            
            if len(links) >= max_links:
                break

        print(f"Número de links encontrados: {len(links)}")
    except Exception as e:
        print(f"Erro durante a coleta de links: {e}")
    return links[:max_links]  # Retorna somente até o limite

def salvar_em_excel(links, search_term):
    try:
        spreadsheet = Workbook()
        sheet = spreadsheet.active
        sheet['A1'] = "NOME DA VAGA"
        sheet['B1'] = "LINK DA VAGA"
        next_line = 2
        
        for link in links:
            text = link.text
            url_link = link.get_attribute("href")
            sheet[f'A{next_line}'] = text
            sheet[f'B{next_line}'] = url_link
            next_line += 1
        
        file_name = f"vagas_links_{search_term}.xlsx"
        spreadsheet.save(file_name)
        print(f"Planilha '{file_name}' criada com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar planilha: {e}")

def verificar_versao_chrome():
    """Verifica a versão do Chrome instalada e retorna a versão como string."""
    try:
        if platform.system() == "Windows":
            process = subprocess.run(['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'], capture_output=True, text=True)
            version_line = process.stdout.split('\n')[2]
            version = version_line.split()[-1]
        elif platform.system() == "Darwin":
            process = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], capture_output=True, text=True)
            version = process.stdout.split()[-1]
        else:
            return None
        return version
    except Exception as e:
        print(f"Erro ao verificar a versão do Chrome: {e}")
        return None

def iniciar_navegador(retries=3, delay=5):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--headless")  # Modo sem interface gráfica
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")

    # Adiciona opções experimentais para tentar forçar compatibilidade
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Verifica a versão do Chrome instalado
    versao_chrome = verificar_versao_chrome()
    print(f"Versão do Chrome instalada: {versao_chrome}")

    # Usar o webdriver_manager para baixar o Chromedriver mais compatível
    service = Service(ChromeDriverManager().install())

    for attempt in range(retries):
        try:
            print(f"Tentando iniciar o navegador Chrome... tentativa {attempt + 1}")
            browser = webdriver.Chrome(service=service, options=chrome_options)
            sleep(5)
            return browser
        except WebDriverException as e:
            print(f"Erro ao iniciar o navegador: {e}. Tentando novamente em {delay} segundos...")
            sleep(delay)

    print("Falha ao iniciar o navegador após múltiplas tentativas.")
    return None

def main():
    file_path_credentials = "credentials.txt"
    credentials = read_credentials(file_path_credentials)
    
    if not credentials:
        print("Credenciais inválidas.")
        return
    
    search_term = input("Digite sua busca: ")
    browser = iniciar_navegador()
    
    if browser:
        try:
            login(browser, credentials)
            ul_element = buscar_vagas(browser, search_term)
            
            if ul_element:
                links = coletar_links(browser, ul_element)
                if links:
                    salvar_em_excel(links, search_term)
        finally:
            print("Encerrando busca")
            browser.quit()

if __name__ == "__main__":
    main()