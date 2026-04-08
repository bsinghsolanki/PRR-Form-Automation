def fill(elements, value, driver):

    for rb in elements:

        if rb.get_attribute("value").lower() == str(value).lower():

            driver.execute_script(
                "arguments[0].click();",
                rb
            )
