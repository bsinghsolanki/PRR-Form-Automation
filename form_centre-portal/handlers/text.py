def fill(element, value, driver):

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        element
    )

    element.clear()
    element.send_keys(str(value))
