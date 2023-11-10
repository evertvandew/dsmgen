"""
Test for the client, built on selenium.
Generates and runs its own server and client.
"""


import subprocess
import os
import time
from dataclasses import fields
from test_frame import prepare, test, run_tests, cleanup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import requests

###############################################################################
## The actual tests.

@prepare
def explorer_tests():
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run("../diagram_tool_generator/generate_tool.py sysml_model.py", shell=True)
    if not os.path.exists('public/src'):
        os.symlink(os.path.abspath('../public/src'), 'public/src')
    import build.sysml_model_data as dm
    db = 'build/data/diagrams.sqlite3'
    if os.path.exists(db):
        os.remove(db)

    server = subprocess.Popen(['/usr/local/bin/python3.11', 'sysml_model_run.py', '5200'], cwd=os.getcwd()+'/build')
    client_url = 'http://localhost:5200/sysml_model.html'
    @cleanup
    def stop_server():
        server.terminate()
        server.poll()

    os.environ['TMPDIR'] =  f'{os.environ["HOME"]}/tmp'
    driver = webdriver.Firefox()
    driver.implicitly_wait(2)
    @cleanup
    def stop_driver():
        driver.close()


    # Class for lines in the explorer window
    line_cls = 'eline'

    @test
    def test_create_block():
        driver.get(client_url)
        # Get the line for the "structural" model
        for attempt in range(5):
            explorer_elements = driver.find_elements(By.ID, f'2')
            if explorer_elements:
                break
        # Right-click on it
        chain = ActionChains(driver)
        chain.context_click(explorer_elements[0]).perform()
        e = explorer_elements[0]
        # Find the menu option to create a 'Block' and click it
        options = [o for o in e.find_elements(By.TAG_NAME, 'li') if o.text == 'Block']
        assert options
        options[0].click()
        # Fill in the name of the new block.
        i = [tag for tag in driver.find_elements(By.TAG_NAME, 'input') if tag.get_attribute("name") == 'name']
        assert i
        i[0].send_keys('test block 1')
        # Click the Ok button
        b = [tag for tag in driver.find_elements(By.CLASS_NAME, 'brython-dialog-button') if tag.text == 'Ok']
        assert b
        b[0].click()

        # Check the new element is in the explorer hierarchy]
        time.sleep(1)
        e = driver.find_elements(By.CSS_SELECTOR, f'.{line_cls}')
        assert len(e) >= 3
        # Check it has ID 3
        e = driver.find_elements(By.ID, f'3')
        assert e
        # Check it is a child of line 2
        e1 = driver.find_elements(By.ID, f'2')
        e2 = e1[0].find_elements(By.ID, f'3')
        assert e2
        # Check the new element is in the database by requesting it using the REST API.
        response = requests.get('http://localhost:5200/data/Block/3')
        assert response.status_code == 200
        assert response.text == '{"order": 0, "Id": 3, "parent": 2, "name": "test block 1", "description": "", "__classname__": "Block"}'

        # Now try to delete it
        # Expand the parent
        e = driver.find_elements(By.ID, f'2')
        c = e[0].find_elements(By.CLASS_NAME, 'caret')
        c[0].click()
        e = driver.find_elements(By.ID, f'3')
        chain.context_click(e[0]).perform()
        options = [o for o in e[0].find_elements(By.TAG_NAME, 'li') if o.text == 'Remove']
        options[0].click()
        b = [tag for tag in driver.find_elements(By.CLASS_NAME, 'brython-dialog-button') if tag.text == 'Ok']
        assert b
        b[0].click()
        # Check it is deleted in the database
        response = requests.get('http://localhost:5200/data/Block/3')
        assert response.status_code == 404
        # Check it is no longer in the explorer
        e = driver.find_elements(By.ID, f'3')
        assert not e

    @test
    def test_show_initial_elements():
        driver.get(client_url)
        ok = False
        for attempt in range(5):
            explorer_elements = driver.find_elements(By.CSS_SELECTOR, f'.{line_cls}')
            if len(explorer_elements) >= 2:
                ok = True
                break
        assert ok, "The two model roots were not found"

if __name__ == '__main__':
    run_tests()