from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import os
import sys

def setup_driver():
    options = Options()
    
    # Fix Chromium path
    if os.path.exists('/usr/bin/chromium'):
        options.binary_location = '/usr/bin/chromium'
    else:
        options.binary_location = '/usr/bin/chromium-browser'
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')  # Uncommented
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')  # Uncommented
    options.add_argument('--headless')  # Added for CI
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Fix chromedriver path
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
    else:
        # Try to find chromedriver in other locations
        service = Service('/usr/lib/chromium-browser/chromedriver')
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)  # Add implicit wait
        return driver
    except Exception as e:
        print(f"Error creating driver: {e}")
        # Fallback: try without specifying service
        try:
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            raise

def login(driver, username, password):
    try:
        driver.get("https://localhost:2443")
        time.sleep(8)  # Increase wait time
        
        # Wait for input fields to appear
        username_field = driver.find_element(By.CSS_SELECTOR, "#username")
        password_field = driver.find_element(By.CSS_SELECTOR, "#password")
        
        username_field.clear()
        username_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
        
        # Find login button with exception handling
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
            # Try to find by text
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
        
        # Check login success
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()
        
        # If still on login page or error message is present
        if "login" in current_url or "error" in page_source or "invalid" in page_source:
            return False
        return True
        
    except Exception as e:
        print(f"Login error: {e}")
        return False

def test_correct_login():
    driver = setup_driver()
    try:
        print("Test: Successful authorization")
        success = login(driver, "root", "0penBmc")
        if success:
            print("✓ Successful authorization passed")
        else:
            print("❌ Successful authorization failed")
        return success
    except Exception as e:
        print(f"❌ Error in successful authorization test: {e}")
        return False
    finally:
        driver.quit()

def test_wrong_password():
    driver = setup_driver()
    try:
        print("Test: Wrong password")
        success = not login(driver, "root", "wrong_password")
        if success:
            print("✓ Wrong password correctly rejected")
        else:
            print("❌ System accepted wrong password")
        return success
    except Exception as e:
        print(f"❌ Error in wrong password test: {e}")
        return False
    finally:
        driver.quit()

def test_account_lockout():
    driver = setup_driver()
    try:
        print("Test: Account lockout")
        # 3 failed login attempts
        for i in range(3):
            result = login(driver, "testuser", f"wrong_pass_{i}")
            print(f"Login attempt {i+1}/3: {'Success' if result else 'Failure'}")
            if i < 2:  # Give time between attempts
                time.sleep(2)
        
        # Check lockout
        success = not login(driver, "testuser", "user10")
        if success:
            print("✓ Account locked after 3 failed attempts")
        else:
            print("❌ Account not locked")
        return success
    except Exception as e:
        print(f"❌ Error in lockout test: {e}")
        return False
    finally:
        driver.quit()

def test_redfish_api_access():
    """Test Redfish API access"""
    driver = setup_driver()
    try:
        print("Test: Redfish API access")
        if not login(driver, "root", "0penBmc"):
            print("❌ Failed to authorize for Redfish check")
            return False
        
        # Check main Redfish endpoint
        driver.get("https://localhost:2443/redfish/v1/")
        time.sleep(8)
        
        # Check that Redfish is working
        page_source = driver.page_source.lower()
        if "redfish" in page_source and "v1" in page_source:
            print("✓ Redfish API available")
            return True
        else:
            print("❌ Redfish API not available or invalid response")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Redfish API: {e}")
        return False
    finally:
        driver.quit()

def test_power_management():
    """Test server power management"""
    driver = setup_driver()
    try:
        print("Test: Server power management")
        if not login(driver, "root", "0penBmc"):
            print("❌ Failed to authorize for power management check")
            return False
        
        # Check power management section
        driver.get("https://localhost:2443/redfish/v1/Systems/system")
        time.sleep(10)
        
        page_text = driver.page_source.lower()
        
        # Check for power management elements
        power_indicators = ["power", "reset", "on", "off", "shutdown", "restart"]
        found_indicators = [indicator for indicator in power_indicators if indicator in page_text]
        
        if found_indicators:
            print(f"✓ Found power management elements: {found_indicators}")
            return True
        else:
            print("❌ Power management not found")
            print("Page content:", page_text[:500])  # Log first 500 characters for debugging
            return False
            
    except Exception as e:
        print(f"❌ Error checking power management: {e}")
        return False
    finally:
        driver.quit()


if __name__ == "__main__":
    # Create log file for Jenkins
    original_stdout = sys.stdout
    try:
        with open('webui-test-log.txt', 'w', encoding='utf-8') as f:
            sys.stdout = f
            
            tests = [
                ("Successful authorization", test_correct_login),
                ("Wrong password", test_wrong_password),
                ("Account lockout", test_account_lockout),
                ("Redfish API access", test_redfish_api_access),
                ("Server power management", test_power_management)  
            ]
            
            print("=== WEBUI TESTS START ===")
            print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            passed = 0
            
            for i, (test_name, test_func) in enumerate(tests, 1):
                try:
                    print(f"\n--- Test {i}: {test_name} ---")
                    result = test_func()
                    status = "✅ PASSED" if result else "❌ FAILED"
                    print(f"Result: {status}")
                    if result:
                        passed += 1
                except Exception as e:
                    print(f"❌ FAILED - Critical error: {e}")
            
            print(f"\n=== SUMMARY: {passed}/{len(tests)} tests passed ===")
            print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"Error writing log: {e}")
    finally:
        sys.stdout = original_stdout
    
    # Also print result to console
    print(f"WebUI tests completed. Results saved to webui-test-log.txt")
    print(f"SUMMARY: {passed}/{len(tests)} tests passed")