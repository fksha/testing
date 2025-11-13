from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import os

def setup_driver():
    options = Options()
    
    # Исправляем путь к Chromium
    if os.path.exists('/usr/bin/chromium'):
        options.binary_location = '/usr/bin/chromium'
    else:
        options.binary_location = '/usr/bin/chromium-browser'
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')  # Раскомментируем
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')  # Раскомментируем
    options.add_argument('--headless')  # Добавляем для CI
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Исправляем путь к chromedriver
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
    else:
        # Пробуем найти chromedriver в других местах
        service = Service('/usr/lib/chromium-browser/chromedriver')
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)  # Добавляем неявное ожидание
        return driver
    except Exception as e:
        print(f"Ошибка при создании драйвера: {e}")
        # Fallback: пробуем без указания service
        try:
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e2:
            print(f"Fallback также не сработал: {e2}")
            raise

def login(driver, username, password):
    try:
        driver.get("https://localhost:2443")
        time.sleep(8)  # Увеличиваем время ожидания
        
        # Ждем появления полей ввода
        username_field = driver.find_element(By.CSS_SELECTOR, "#username")
        password_field = driver.find_element(By.CSS_SELECTOR, "#password")
        
        username_field.clear()
        username_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
        
        # Поиск кнопки входа с обработкой исключений
        button_found = False
        for selector in ["button[type='submit']", "button", "input[type='submit']", ".btn-primary"]:
            try:
                button = driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    button_found = True
                    break
            except:
                continue
        
        if not button_found:
            # Пробуем найти по тексту
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if button.text.lower() in ["login", "sign in", "войти", "вход"]:
                        button.click()
                        button_found = True
                        break
            except:
                pass
        
        time.sleep(5)
        
        # Проверяем успешность логина
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()
        
        # Если остались на странице логина или есть сообщение об ошибке
        if "login" in current_url or "error" in page_source or "invalid" in page_source:
            return False
        return True
        
    except Exception as e:
        print(f"Ошибка при логине: {e}")
        return False

def test_correct_login():
    driver = setup_driver()
    try:
        print("Тест: Успешная авторизация")
        success = login(driver, "root", "0penBmc")
        if success:
            print("✓ Успешная авторизация прошла")
        else:
            print("❌ Успешная авторизация не удалась")
        return success
    except Exception as e:
        print(f"❌ Ошибка в тесте успешной авторизации: {e}")
        return False
    finally:
        driver.quit()

def test_wrong_password():
    driver = setup_driver()
    try:
        print("Тест: Неверный пароль")
        success = not login(driver, "root", "wrong_password")
        if success:
            print("✓ Неверный пароль правильно отклонен")
        else:
            print("❌ Система приняла неверный пароль")
        return success
    except Exception as e:
        print(f"❌ Ошибка в тесте неверного пароля: {e}")
        return False
    finally:
        driver.quit()

def test_account_lockout():
    driver = setup_driver()
    try:
        print("Тест: Блокировка учетной записи")
        # 3 неудачные попытки входа
        for i in range(3):
            result = login(driver, "testuser", f"wrong_pass_{i}")
            print(f"Попытка входа {i+1}/3: {'Успех' if result else 'Неудача'}")
            if i < 2:  # Даем время между попытками
                time.sleep(2)
        
        # Проверка блокировки
        success = not login(driver, "testuser", "user10")
        if success:
            print("✓ Учетная запись заблокирована после 3 неудачных попыток")
        else:
            print("❌ Учетная запись не заблокирована")
        return success
    except Exception as e:
        print(f"❌ Ошибка в тесте блокировки: {e}")
        return False
    finally:
        driver.quit()

def test_redfish_api_access():
    """Тест доступа к Redfish API"""
    driver = setup_driver()
    try:
        print("Тест: Доступ к Redfish API")
        if not login(driver, "root", "0penBmc"):
            print("❌ Не удалось авторизоваться для проверки Redfish")
            return False
        
        # Проверяем основной Redfish endpoint
        driver.get("https://localhost:2443/redfish/v1/")
        time.sleep(8)
        
        # Проверяем что Redfish работает
        page_source = driver.page_source.lower()
        if "redfish" in page_source and "v1" in page_source:
            print("✓ Redfish API доступен")
            return True
        else:
            print("❌ Redfish API не доступен или неверный ответ")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке Redfish API: {e}")
        return False
    finally:
        driver.quit()

def test_power_management():
    """Тест управления питанием сервера"""
    driver = setup_driver()
    try:
        print("Тест: Управление питанием сервера")
        if not login(driver, "root", "0penBmc"):
            print("❌ Не удалось авторизоваться для проверки управления питанием")
            return False
        
        # Проверяем раздел управления питанием
        driver.get("https://localhost:2443/redfish/v1/Systems/system")
        time.sleep(10)
        
        page_text = driver.page_source.lower()
        
        # Проверяем наличие элементов управления питанием
        power_indicators = ["power", "reset", "on", "off", "shutdown", "restart"]
        found_indicators = [indicator for indicator in power_indicators if indicator in page_text]
        
        if found_indicators:
            print(f"✓ Найдены элементы управления питанием: {found_indicators}")
            return True
        else:
            print("❌ Управление питанием не найдено")
            print("Содержимое страницы:", page_text[:500])  # Логируем первые 500 символов для отладки
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке управления питанием: {e}")
        return False
    finally:
        driver.quit()


if __name__ == "__main__":
    # Создаем лог-файл для Jenkins
    original_stdout = sys.stdout
    try:
        with open('webui-test-log.txt', 'w', encoding='utf-8') as f:
            sys.stdout = f
            
            tests = [
                ("Успешная авторизация", test_correct_login),
                ("Неверный пароль", test_wrong_password),
                ("Блокировка учетной записи", test_account_lockout),
                ("Доступ к Redfish API", test_redfish_api_access),
                ("Управление питанием сервера", test_power_management)  
            ]
            
            print("=== ЗАПУСК WEBUI ТЕСТОВ ===")
            print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            passed = 0
            
            for i, (test_name, test_func) in enumerate(tests, 1):
                try:
                    print(f"\n--- Тест {i}: {test_name} ---")
                    result = test_func()
                    status = "✅ PASSED" if result else "❌ FAILED"
                    print(f"Результат: {status}")
                    if result:
                        passed += 1
                except Exception as e:
                    print(f"❌ FAILED - Критическая ошибка: {e}")
            
            print(f"\n=== ИТОГ: {passed}/{len(tests)} тестов пройдено ===")
            print(f"Время завершения: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")
    finally:
        sys.stdout = original_stdout
    
    # Также выводим результат в консоль
    print(f"WebUI тесты завершены. Результаты сохранены в webui-test-log.txt")
    print(f"ИТОГ: {passed}/{len(tests)} тестов пройдено")