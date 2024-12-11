import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Define initial passwords
initial_config = {
    'credentials': {
        'usernames': {
            'admin': {
                'email': 'admin@example.com',
                'name': 'Administrator',
                'password': None,  # Will be set to hashed 'Admin0123!'
                'role': 'admin'
            },
            'user1': {
                'email': 'user1@thinkvideo.com',
                'name': 'User One',
                'password': None,  # Will be set to hashed 'Password01!'
                'client': 'ThinkVideo',
                'role': 'user'
            },
            'user2': {
                'email': 'user2@choicemaster.com',
                'name': 'User Two',
                'password': None,  # Will be set to hashed 'Password02!'
                'client': 'ChoiceMaster',
                'role': 'user'
            }
        }
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'random_signature_key_12345',
        'name': 'mindsearch_auth_cookie'
    }
}

# List of plain passwords (in same order as usernames)
passwords = ['Admin0123!', 'Password01!', 'Password02!']
usernames = list(initial_config['credentials']['usernames'].keys())

# create hasher
hasher = stauth.Hasher(passwords)

# Generate password hashes
for username, password in zip(usernames, passwords):
    initial_config['credentials']['usernames'][username]['password'] = hasher.hash(password)

# Save to config file
with open('config_login.yaml', 'w') as file:
    yaml.dump(initial_config, file, default_flow_style=False)

print("Generated config_login.yaml with the following credentials:")
print("\nAdmin User:")
print("Username: admin")
print("Password: Admin01!")
print("\nTest Users:")
print("Username: user1")
print("Password: Password01!")
print("Username: user2")
print("Password: Password02!")
