from browser import document, ajax, window, html, console, bind
import json

# Function to get the current database
def get_current_database(_request=None):
    console.log("getting current database")
    ajax.get('/current_database', mode='json', oncomplete=update_current_database)

# Function to update the current database display
def update_current_database(req):
    if selector := document.get(selector='#database-selector'):
        # Selector is a list of objects found. Select the first one of them.
        selector = selector[0]
        current_db = req.json
        selector.clear()
        _ = selector <= f"Current DB: {current_db}"
        selector.data_value = current_db

# Function to display the database management dialog
def database_management_dialog(ev):
    # Create the dialog elements
    dialog = html.DIALOG(id='database-dialog')
    _ = dialog <= html.H2('Database Management')
    _ = dialog <= html.SPAN(id='current-database')
    _ = dialog <= (selector := html.SELECT(id='database-select'))
    _ = dialog <= (new_db_name := html.INPUT(id='new-database-input', type='text', placeholder='New database name'))
    _ = dialog <= (create_btn := html.BUTTON('Create', id='create-button'))
    _ = dialog <= (delete_btn := html.BUTTON('Delete', id='delete-button'))
    _ = dialog <= (close_btn := html.BUTTON('Close', id='close-button'))

    @bind(close_btn, 'click')
    def close_dialog(ev):
        dialog.close()
        window.location.reload()

    # Function to fetch databases
    def fetch_databases(_request=None):
        ajax.get('/databases', mode='json', oncomplete=update_dropdown)

    # Function to update dropdown with databases
    def update_dropdown(req):
        databases = req.json
        selector.clear()
        for db in databases:
            if db == document['database-selector'].data_value:
                _ = selector <= html.OPTION(db, selected=True)
            else:
                _ = selector <= html.OPTION(db)

    # Function to activate selected database
    @bind(selector, 'change')
    def activate_database(ev):
        db_name = selector.value
        ajax.put(f'/databases/{db_name}/activate', oncomplete=get_current_database)

    # Function to delete selected database
    @bind(delete_btn, 'click')
    def delete_database(ev):
        db_name = selector.value
        if window.confirm(f'Are you sure you want to delete {db_name}?'):
            ajax.delete(f'/databases/{db_name}', oncomplete=fetch_databases)

    # Function to create new database
    @bind(create_btn, 'click')
    def create_database(ev):
        db_name = new_db_name.value
        ajax.post('/databases', data=json.dumps({'name': db_name}), headers={'Content-Type': 'application/json'},
                  oncomplete=fetch_databases)

    # Fetch the databases and update the dropdown
    fetch_databases()

    # Add the dialog to the document
    _ = document <= dialog

    # Show the dialog
    dialog.showModal()

# Function to create the database selector label
def database_selector():
    label = html.LABEL('Select Database', id='database-selector')
    label.bind('click', database_management_dialog)
    get_current_database()
    return label
