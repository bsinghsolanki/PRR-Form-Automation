def fill(element, value, driver):

    driver.execute_script(
        "arguments[0].value = arguments[1];",
        element,
        value
    )
