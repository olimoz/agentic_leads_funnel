# mkhorasani/Streamlit-Authenticator Public

A secure authentication module to manage user access in a Streamlit application.

### License

View license

1.7k stars 260 forks 

# Table of Contents

- Quickstart
- Installation
- Creating a config file
- Setup
- Creating a login widget
- Creating a guest login button 🚀 NEW
- Authenticating users
- Creating a reset password widget
- Creating a new user registration widget
- Creating a forgot password widget
- Creating a forgot username widget
- Creating an update user details widget
- Updating the config file
- License

### 1. Quickstart

- Check out the demo app.
- Feel free to visit the API reference.
- And finally follow the tutorial below.

### 2. Installation

Streamlit-Authenticator is distributed via PyPI:

```
pip install streamlit-authenticator
```

Using Streamlit-Authenticator is as simple as importing the module and calling it to verify your user's credentials.

```
import streamlit as st
import streamlit_authenticator as stauth
```

### 3. Creating a config file

- Create a YAML config file and add to it your user's credentials: including username, email, first name, last name, and password (plain text passwords will be hashed automatically).
- Enter a name, random key, and number of days to expiry, for a re-authentication cookie that will be stored on the client's browser to enable password-less re-authentication. If you do not require re-authentication, you may set the number of days to expiry to 0.
- Define an optional list of pre-authorized emails of users who are allowed to register and add their credentials to the config file using the register_user widget.
- Add the optional configuration parameters for OAuth2 if you wish to use the experimental_guest_login button.
- Please remember to update the config file (as shown in step 13) whenever the contents are modified or after using any of the widgets or buttons.

```yaml
cookie:
  expiry_days: 30
  key: some_signature_key # Must be a string
  name: some_cookie_name
credentials:
  usernames:
    jsmith:
      email: jsmith@gmail.com
      failed_login_attempts: 0 # Will be managed automatically
      first_name: John
      last_name: Smith
      logged_in: False # Will be managed automatically
      password: abc # Will be hashed automatically
      roles: # Optional
      - admin
      - editor
      - viewer
```

### 4. Setup

Subsequently import the config file into your script and create an authentication object.

```python
import yaml
from yaml.loader import SafeLoader

with open('../config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
```

Plain text passwords will be hashed automatically by default, however, for a large number of users it is recommended to pre-hash the passwords in the credentials using the Hasher.hash_passwords function.

Parameters:
- credentials: dict
  - The credentials dict with plain text passwords.

Returns:
- dict
  - The credentials dict with hashed passwords.

### 5. Creating a login widget

You can render the login widget as follows:

```python
try:
    authenticator.login()
except Exception as e:
    st.error(e)
```

Parameters:
- location: str, {'main', 'sidebar', 'unrendered'}, default 'main'
  - Specifies the location of the login widget.
- max_concurrent_users: int, optional, default None
  - Limits the number of concurrent users.
- max_login_attempts: int, optional, default None
  - Limits the number of failed login attempts.
- fields: dict, optional
  - Customizes the text of headers, buttons and other fields.
- captcha: bool, default False
  - Specifies the captcha requirement for the login widget
- single_session: bool, default False
  - Disables the ability for the same user to log in multiple sessions
- clear_on_submit: bool, default False
  - Specifies the clear on submit setting
- key: str, default 'Login'
  - Unique key provided to widget
- callback: callable, optional, default None
  - Callback function that will be invoked on form submission

### 6. Creating a guest login button

You may use the experimental_guest_login button to log in non-registered users with their Google or Microsoft accounts using OAuth2.

```python
try:
    authenticator.experimental_guest_login('Login with Google',
                                         provider='google',
                                         oauth2=config['oauth2'])
except Exception as e:
    st.error(e)
```

Parameters:
- button_name: str, default 'Guest login'
  - Rendered name of the guest login button
- location: str, {'main', 'sidebar'}, default 'main'
  - Specifies the location of the guest login button
- provider: str, {'google', 'microsoft'}, default 'google'
  - Selection for OAuth2 provider
- oauth2: dict, optional, default None
  - Configuration parameters for OAuth2 authentication
- max_concurrent_users: int, optional, default None
  - Limits the number of concurrent users
- single_session: bool, default False
  - Disables multiple sessions for same user
- roles: list, optional, default None
  - User roles for guest users
- callback: callable, optional, default None
  - Callback function for button press

### 7. Authenticating users

You can retrieve the name, authentication status, and username from Streamlit's session state:

```python
if st.session_state['authentication_status']:
    authenticator.logout()
    st.write(f'Welcome *{st.session_state["name"]}*')
    st.title('Some content')
elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')
```

### 8. Creating a reset password widget

You may use the reset_password widget to allow a logged in user to modify their password:

```python
if st.session_state['authentication_status']:
    try:
        if authenticator.reset_password(st.session_state['username']):
            st.success('Password modified successfully')
    except Exception as e:
        st.error(e)
```

Parameters:
- username: str
  - Username of the user to reset password for
- location: str, {'main', 'sidebar'}, default 'main'
- fields: dict, optional
  - Customizes text fields
- clear_on_submit: bool, default False
- key: str, default 'Reset password'
- callback: callable, optional, default None

### 9. Creating a new user registration widget

Allow users to sign up using the register_user widget:

```python
try:
    email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user()
    if email_of_registered_user:
        st.success('User registered successfully')
except Exception as e:
    st.error(e)
```

### 10. Creating a forgot password widget

The forgot_password widget allows users to generate a new random password:

```python
try:
    username_of_forgotten_password, email_of_forgotten_password, new_random_password = authenticator.forgot_password()
    if username_of_forgotten_password:
        st.success('New password to be sent securely')
except Exception as e:
    st.error(e)
```

### 11. Creating a forgot username widget

Allow users to retrieve forgotten usernames:

```python
try:
    username_of_forgotten_username, email_of_forgotten_username = authenticator.forgot_username()
    if username_of_forgotten_username:
        st.success('Username to be sent securely')
except Exception as e:
    st.error(e)
```

### 12. Creating an update user details widget

Allow logged in users to update their details:

```python
if st.session_state['authentication_status']:
    try:
        if authenticator.update_user_details(st.session_state['username']):
            st.success('Entries updated successfully')
    except Exception as e:
        st.error(e)
```

### 13. Updating the config file

Ensure the config file is re-saved after modifications:

```python
with open('../config.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)
```

## License

This project is proprietary software. The use of this software is governed by the terms specified in the LICENSE file. Unauthorized copying, modification, or distribution of this software is prohibited.

## About

A secure authentication module to manage user access in a Streamlit application.

### Topics

python oauth2 authentication streamlit streamlit-component

### Stats

- 1.7k stars
- 19 watching
- 260 forks

## Languages

Python 100.0%