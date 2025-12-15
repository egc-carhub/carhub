from selenium.webdriver.common.by import By


from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


class TestSelenium:
    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}

    def teardown_method(self, method):
        close_driver(self.driver)

    def test_selenium(self):
        self.driver.get(get_host_for_selenium_testing())
        self.driver.set_window_size(1854, 1168)
        self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        self.driver.find_element(By.ID, "email").click()
        self.driver.find_element(By.ID, "email").send_keys("user3@example.com")
        self.driver.find_element(By.ID, "password").send_keys("1234")
        self.driver.find_element(By.ID, "submit").click()
        self.driver.find_element(By.LINK_TEXT, "Sample dataset 4").click()
        self.driver.find_element(By.LINK_TEXT, "Doe, Jane").click()
        self.driver.find_element(By.ID, "follow-btn").click()
        self.driver.find_element(By.ID, "follow-btn").click()
        self.driver.find_element(By.ID, "follow-btn").click()
        self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(5) .align-middle:nth-child(2)").click()
        self.driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) > .mb-1:nth-child(2)").click()
        self.driver.find_element(By.ID, "membership-btn").click()
        self.driver.find_element(By.ID, "membership-btn").click()
        self.driver.find_element(By.ID, "follow-community-btn").click()
        self.driver.find_element(By.ID, "follow-community-btn").click()
        self.driver.find_element(By.ID, "follow-community-btn").click()
        self.driver.find_element(By.LINK_TEXT, "Back to Communities List").click()
        self.driver.find_element(By.LINK_TEXT, "Smith, Alice").click()
        self.driver.find_element(By.CSS_SELECTOR, ".dropdown-item:nth-child(5)").click()
