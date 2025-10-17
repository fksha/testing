from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

def setup_driver():
    options = Options()
    options.binary_location = '/usr/bin/chromium-browser'
    options.add_argument('--no-sandbox')
    #options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    #options.add_argument('--allow-insecure-localhost')
    
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=options)

def login(driver, username, password):
    driver.get("https://localhost:2443")
    time.sleep(6)
    
    driver.find_element(By.CSS_SELECTOR, "#username").send_keys(username)
    driver.find_element(By.CSS_SELECTOR, "#password").send_keys(password)
    
    # Поиск кнопки входа
    for selector in ["button[type='submit']", "button", "input[type='submit']"]:
        try:
            driver.find_element(By.CSS_SELECTOR, selector).click()
            break
        except:
            continue
    
    time.sleep(5)
    return "login" not in driver.current_url.lower()

def test_correct_login():
    driver = setup_driver()
    try:
        success = login(driver, "root", "0penBmc")
        return success
    finally:
        driver.quit()

def test_wrong_password():
    driver = setup_driver()
    try:
        success = not login(driver, "root", "wrong_password")
        return success
    finally:
        driver.quit()

def test_account_lockout():
    driver = setup_driver()
    try:
        # 3 неудачные попытки входа
        for i in range(3):
            login(driver, "testuser", f"wrong_pass_{i}")
            print(f"Попытка входа {i+1}/3")
        
        # Проверка блокировки
        success = not login(driver, "testuser", "user10")
        return success
    finally:
        driver.quit()

def test_redfish_api_access():
    """Тест доступа к Redfish API"""
    driver = setup_driver()
    try:
        if not login(driver, "root", "0penBmc"):
            return False
        
        # Проверяем основной Redfish endpoint
        driver.get("https://localhost:2443/redfish/v1/")
        time.sleep(6)
        # Простая проверка что Redfish работает
        if "redfish" in driver.page_source.lower():
            print("✓ Redfish API доступен")
            return True
        else:
            print("❌ Redfish API не доступен")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        driver.quit()

def test_power_management():
    """Тест управления питанием сервера"""
    driver = setup_driver()
    try:
        if not login(driver, "root", "0penBmc"):
            return False
        
        # Проверяем раздел управления питанием
        driver.get("https://localhost:2443/redfish/v1/Systems/system")
        time.sleep(15)
        
        page_text = driver.page_source.lower()
        
        # Проверяем наличие элементов управления питанием
        if "power" in page_text:
            print("✓ Найдены элементы управления питанием")
            return True
        else:
            print("❌ Управление питанием не найдено")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        driver.quit()


if __name__ == "__main__":
    tests = [
        ("Успешная авторизация", test_correct_login),
        ("Неверный пароль", test_wrong_password),
        ("Блокировка учетной записи", test_account_lockout),
        ("Доступ к Redfish API", test_redfish_api_access),
        ("Управлениe питанием сервера", test_power_management)  
    ]
    
    print("=== ЗАПУСК ТЕСТОВ ===")
    passed = 0
    
    for i, (test_name, test_func) in enumerate(tests, 1):
        try:
            result = test_func()
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"Тест {i}: {test_name}: {status}")
            if result:
                passed += 1
        except Exception as e:
            print(f"Тест {i}: {test_name}: ❌ FAILED - {e}")
    
    print(f"\n=== ИТОГ: {passed}/{len(tests)} тестов пройдено ===")