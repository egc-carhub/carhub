from selenium.webdriver.common.by import By

from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


class TestContador:
    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}

    def teardown_method(self, method):
        close_driver(self.driver)

    def test_contador(self):
        self.driver.get(get_host_for_selenium_testing())
        self.driver.set_window_size(1854, 1048)
        self.driver.find_element(By.LINK_TEXT, "Login").click()
        self.driver.find_element(By.ID, "email").click()
        self.driver.find_element(By.ID, "email").send_keys("user3@example.com")
        self.driver.find_element(By.ID, "password").click()
        self.driver.find_element(By.ID, "password").send_keys("1234")
        self.driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
        wait = WebDriverWait(self.driver, 10)
        dataset_link = wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Sample dataset")))
        dataset_link.click()
        self.driver.find_element(By.LINK_TEXT, "Download all (442 bytes)").click()
        self.driver.find_element(By.CSS_SELECTOR, ".col-xl-4").click()
        self.driver.refresh()
        self.driver.find_element(By.LINK_TEXT, "Download all (442 bytes)").click()
        self.driver.find_element(By.CSS_SELECTOR, ".col-xl-4").click()
        self.driver.refresh()
        self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(2) .align-middle:nth-child(2)").click()
