def fill(elements, value, driver):

    values = str(value).lower().split("|")

    for cb in elements:

        if cb.get_attribute("value").lower() in values:

            driver.execute_script(
                "arguments[0].click();",
                cb
            )
