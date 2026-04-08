from selenium.webdriver.support.ui import Select

def fill(element, value, driver):

    Select(element).select_by_visible_text(str(value))
