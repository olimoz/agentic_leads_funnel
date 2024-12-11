import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="Lead Funnel Manager",
    page_icon="🎯",
    layout="wide"
)

import pandas as pd
from pathlib import Path
import os
import re
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Constants
BLOB_CONTAINER_PATH = "../clients"
DEFAULT_PROMPTS_PATH = "../default_prompts"
PROMPTS = {
    "search": "prompt_searchproposalagent.txt",
    "url_extraction": "prompt_urlextractionagent.txt",
    "scoring": "prompt_targetscoreagent.txt",
    "comparison": "prompt_resultscomparisonagent.txt",
    "ranking": "prompt_searchresultsrankingagent.txt",
    "email_template": "template_email.md",
    "business_description": "prompt_businessdescription.md",
    "email_instructions": "prompt_emailproposalagent.txt"
}

class LeadFunnelManagerUI:
    def __init__(self):
        """Initialize the UI"""
        # Load authentication config
        with open('config_login.yaml') as file:
            self.config = yaml.load(file, Loader=SafeLoader)

        # Create an authentication object
        self.authenticator = stauth.Authenticate(
            credentials=self.config['credentials'],
            cookie_name=self.config['cookie']['name'],
            key=self.config['cookie']['key'],
            cookie_expiry_days=self.config['cookie']['expiry_days']
        )
        
        # Initialize client-related attributes
        self.username = None
        self.is_admin = False
        self.client_list = []
        self.current_client = None
        
        # Load client data
        self.load_client_data()
        
        # Initialize section state
        if 'active_section' not in st.session_state:
            st.session_state.active_section = None
        
        # Add custom CSS for button and expander styling
        st.markdown('<style>' + open('styles.css').read() + '</style>', unsafe_allow_html=True)
               
    def setup_page(self):
        """Configure the Streamlit page"""
        st.title("Lead Funnel Manager")

    def load_client_data(self):
        """Load client data from the filesystem"""
        # Create base container directory if it doesn't exist
        os.makedirs(BLOB_CONTAINER_PATH, exist_ok=True)
        
        # Get username from session state if available
        if st.session_state.get("authentication_status"):
            self.username = st.session_state["username"]
            user_info = self.config['credentials']['usernames'][self.username]
            
            # Check if user is admin
            self.is_admin = user_info.get('role') == 'admin'
            
            # Get client list
            if self.is_admin:
                self.client_list = user_info.get('client', [])  # For admin, client is a list
                # Create directories for all clients
                for client in self.client_list:
                    os.makedirs(os.path.join(BLOB_CONTAINER_PATH, client), exist_ok=True)
                # Set current client to first in list if not already set
                if not self.current_client and self.client_list:
                    self.current_client = self.client_list[0]
            else:
                client = user_info.get('client')  # For regular users, client is a string
                if client:
                    self.client_list = [client]
                    self.current_client = client
                    # Create client directory
                    os.makedirs(os.path.join(BLOB_CONTAINER_PATH, client), exist_ok=True)
                else:
                    self.client_list = []

    def extract_variables(self, text):
        """Extract all variables in the format {variable_name} from text"""
        return set(re.findall(r'\{([^}]+)\}', text))

    def read_prompt_file(self, prompt_file):
        """Read content from a prompt file"""
        if not self.current_client:
            return ""
        try:
            file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, prompt_file)
            with open(file_path, 'r') as f:
                content = f.read()
                return content
        except Exception as e:
            st.warning(f"Could not read prompt file: {str(e)}")
            return ""

    def read_default_prompt(self, prompt_file):
        """Read content from the default prompt file"""
        try:
            file_path = os.path.join(DEFAULT_PROMPTS_PATH, prompt_file)
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            st.warning(f"Could not read default prompt: {str(e)}")
            return ""

    def save_prompt_file(self, prompt_file, new_content):
        """Save content to a prompt file with variable validation"""
        if not self.current_client:
            st.error("Please select a client first")
            return False
        try:
            # Extract variables from new content
            new_variables = self.extract_variables(new_content)
            
            # Get original variables from session state
            vars_key = f"vars_{prompt_file}"
            if vars_key not in st.session_state:
                st.error("Original prompt content not loaded properly")
                return False
                
            missing_vars = st.session_state[vars_key] - new_variables
            if missing_vars:
                st.error(f"Cannot remove required variables: {', '.join(missing_vars)}")
                return False

            # If validation passes, save the file
            client_dir = os.path.join(BLOB_CONTAINER_PATH, self.current_client)
            os.makedirs(client_dir, exist_ok=True)
            file_path = os.path.join(client_dir, prompt_file)
            with open(file_path, 'w') as f:
                f.write(new_content)
            return True
        except Exception as e:
            st.error(f"Error saving prompt: {str(e)}")
            return False

    def prompt_editor_section(self, title, prompt_file, height=200):
        """Generic prompt editor section with default option"""
        # Initialize session state for this prompt if not exists
        text_key = f"textarea_{prompt_file}"
        vars_key = f"vars_{prompt_file}"
        
        if text_key not in st.session_state:
            content = self.read_prompt_file(prompt_file)
            st.session_state[text_key] = content
            st.session_state[vars_key] = self.extract_variables(content)
        
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button(f"Use Default", key=f"default_{prompt_file}", type="secondary"):
                default_content = self.read_default_prompt(prompt_file)
                if default_content:
                    st.session_state[text_key] = default_content
                    st.session_state[vars_key] = self.extract_variables(default_content)
                    st.rerun()
            
            st.write("") # Add some spacing
            if st.button(f"Reset", key=f"reset_{prompt_file}", type="secondary"):
                saved_content = self.read_prompt_file(prompt_file)
                if saved_content:
                    st.session_state[text_key] = saved_content
                    st.session_state[vars_key] = self.extract_variables(saved_content)
                    st.rerun()
        
        with col1:
            new_prompt = st.text_area(
                f"Edit {title} Prompt",
                height=height,
                key=text_key
            )
        
        return new_prompt

    def client_selector(self):
        """Display client selector for admin, or show current client for regular users"""
        if self.is_admin and self.client_list:
            # Admin can select any client
            selected_client = st.sidebar.selectbox(
                "Select Client",
                options=self.client_list,
                index=self.client_list.index(self.current_client) if self.current_client in self.client_list else 0
            )
            self.current_client = selected_client
        else:
            # Regular users just see their assigned client
            if self.current_client:
                st.sidebar.markdown(f"**Client:** {self.current_client}")
            
        return self.current_client

    def _validate_contacts_df(self, df):
        """Validate that dataframe has required columns in correct order"""
        required_columns = ['First Name', 'Last Name', 'Company']
        if not all(col in df.columns for col in required_columns):
            return False
        # Check if the required columns are in the correct order
        df_columns = df.columns.tolist()
        required_indices = [df_columns.index(col) for col in required_columns]
        return required_indices == sorted(required_indices)

    def upload_contacts_section(self):
        """Section for uploading and managing contact lists"""
        with st.expander("1. Upload & Manage List of Contacts"):
            # Display current contacts first
            st.write("### Current Contacts")
            if 'contacts_df' not in st.session_state:
                st.session_state.contacts_df = None
                # Try to load existing file
                if self.current_client:
                    try:
                        file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.xlsx")
                        if os.path.exists(file_path):
                            df = pd.read_excel(file_path)
                            if self._validate_contacts_df(df):
                                st.session_state.contacts_df = df
                    except Exception:
                        pass

            if st.session_state.contacts_df is not None:
                edited_df = st.data_editor(
                    st.session_state.contacts_df,
                    num_rows="dynamic",
                    key="contact_editor"
                )
                
                # Save changes if the dataframe was modified
                if not edited_df.equals(st.session_state.contacts_df) and self.current_client:
                    try:
                        # Create backup of current file
                        file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.xlsx")
                        if os.path.exists(file_path):
                            backup_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.backup.xlsx")
                            os.rename(file_path, backup_path)
                        
                        # Save edited dataframe
                        edited_df.to_excel(file_path, index=False)
                        st.session_state.contacts_df = edited_df
                        st.success("Changes saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving changes: {str(e)}")
            else:
                st.info("No contacts loaded. Please upload a contacts file or select a client with existing contacts.")

            st.write("---")
            st.write("### Update Contacts")
            
            col1, col2 = st.columns([4, 1])
            
            with col2:
                st.write("")  # Spacing
                if st.button("Use Saved", type="secondary"):
                    if self.current_client:
                        try:
                            file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.xlsx")
                            if os.path.exists(file_path):
                                df = pd.read_excel(file_path)
                                if self._validate_contacts_df(df):
                                    st.session_state.contacts_df = df
                                    st.success("Loaded saved contacts file.")
                                else:
                                    st.error("Saved file is missing required columns.")
                            else:
                                st.warning("No saved contacts file found.")
                        except Exception as e:
                            st.error(f"Error loading saved file: {str(e)}")
                    else:
                        st.error("Please select a client first.")
            
            with col1:
                uploaded_file = st.file_uploader(
                    "Upload Contact List (must be .xlsx with columns: First Name, Last Name, Company)", 
                    type=['xlsx']
                )
                
                if uploaded_file:
                    try:
                        df = pd.read_excel(uploaded_file)
                        if self._validate_contacts_df(df):
                            if self.current_client:
                                # Create backup of existing file if it exists
                                file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.xlsx")
                                if os.path.exists(file_path):
                                    backup_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.backup.xlsx")
                                    os.rename(file_path, backup_path)
                                
                                # Save new file
                                df.to_excel(file_path, index=False)
                                st.session_state.contacts_df = df
                                st.success("File uploaded and saved successfully!")
                                st.rerun()  # Refresh to show new data
                            else:
                                st.error("Please select a client first.")
                        else:
                            st.error("File must contain columns: First Name, Last Name, Company (in this order)")
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")
                
                if self.current_client:
                    backup_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.backup.xlsx")
                    if os.path.exists(backup_path):
                        if st.button("Restore Previous Version", type="secondary"):
                            try:
                                file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_tasks.xlsx")
                                os.rename(backup_path, file_path)
                                df = pd.read_excel(file_path)
                                if self._validate_contacts_df(df):
                                    st.session_state.contacts_df = df
                                    st.success("Previous version restored!")
                                    st.rerun()
                                else:
                                    st.error("Previous version has invalid format.")
                                    # Restore the backup
                                    os.rename(file_path, backup_path)
                            except Exception as e:
                                st.error(f"Error restoring backup: {str(e)}")

    def search_strategy_section(self):
        """Section for creating search strategy"""
        with st.expander("2. Create Search Strategy"):
            new_prompt = self.prompt_editor_section(
                "Search Strategy",
                PROMPTS['search']
            )
            if st.button("Save Search Strategy", type="secondary"):
                if self.save_prompt_file(PROMPTS['search'], new_prompt):
                    st.success("Search strategy saved successfully!")

    def execute_searches_section(self):
        """Section for executing searches"""
        with st.expander("3. Execute Searches"):
            st.info("This is an automated step. No configuration required.")
            if st.button("Run Searches", type="secondary"):
                st.info("Search execution initiated...")

    def extract_links_section(self):
        """Section for extracting key links"""
        with st.expander("4. Extract Key Links"):
            new_prompt = self.prompt_editor_section(
                "URL Extraction",
                PROMPTS['url_extraction']
            )
            if st.button("Save URL Extraction Settings", type="secondary"):
                if self.save_prompt_file(PROMPTS['url_extraction'], new_prompt):
                    st.success("URL extraction settings saved successfully!")

    def score_potential_section(self):
        """Section for scoring business potential"""
        with st.expander("5. Score Business Potential"):
            new_prompt = self.prompt_editor_section(
                "Scoring",
                PROMPTS['scoring']
            )
            if st.button("Save Scoring Criteria", type="secondary"):
                if self.save_prompt_file(PROMPTS['scoring'], new_prompt):
                    st.success("Scoring criteria saved successfully!")

    def assess_novelty_section(self):
        """Section for assessing novelty"""
        with st.expander("6. Assess Novelty"):
            new_prompt = self.prompt_editor_section(
                "Comparison",
                PROMPTS['comparison']
            )
            if st.button("Save Novelty Assessment", type="secondary"):
                if self.save_prompt_file(PROMPTS['comparison'], new_prompt):
                    st.success("Novelty assessment settings saved successfully!")

    def rank_prospects_section(self):
        """Section for ranking prospects"""
        with st.expander("7. Rank Prospects"):
            new_prompt = self.prompt_editor_section(
                "Ranking",
                PROMPTS['ranking']
            )
            if st.button("Save Ranking Criteria", type="secondary"):
                if self.save_prompt_file(PROMPTS['ranking'], new_prompt):
                    st.success("Ranking criteria saved successfully!")

    def compose_communications_section(self):
        """Section for composing communications"""
        with st.expander("8. Compose Communications"):
            st.subheader("Email Template")
            template_prompt = self.prompt_editor_section(
                "Email Template",
                PROMPTS['email_template']
            )
            if st.button("Save Email Template", type="secondary"):
                if self.save_prompt_file(PROMPTS['email_template'], template_prompt):
                    st.success("Email template saved successfully!")

            st.subheader("Company Information")
            business_prompt = self.prompt_editor_section(
                "Company Information",
                PROMPTS['business_description']
            )
            if st.button("Save Company Information", type="secondary"):
                if self.save_prompt_file(PROMPTS['business_description'], business_prompt):
                    st.success("Company information saved successfully!")

            st.subheader("Email Drafting Instructions")
            instructions_prompt = self.prompt_editor_section(
                "Email Drafting Instructions",
                PROMPTS['email_instructions']
            )
            if st.button("Save Email Instructions", type="secondary"):
                if self.save_prompt_file(PROMPTS['email_instructions'], instructions_prompt):
                    st.success("Email instructions saved successfully!")

    def load_search_history(self):
        """Load search history from parquet file"""
        if not self.current_client:
            return None
        try:
            file_path = os.path.join(BLOB_CONTAINER_PATH, self.current_client, "df_search_history.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                # Ensure search_date is datetime
                if 'search_date' in df.columns:
                    df['search_date'] = pd.to_datetime(df['search_date'])
                return df
            else:
                st.warning("No search history found for this client")
                return None
        except Exception as e:
            st.error(f"Error loading search history: {str(e)}")
            return None

    def results_section(self):
        """Section for viewing and exporting results"""
        with st.expander("9. View & Export Results"):
            df = self.load_search_history()
            
            if df is not None and not df.empty:
                st.subheader("Search History")
                
                # Initial sort by search_date (newest first)
                df_sorted = df.sort_values(by='search_date', ascending=False)
                
                # Initialize pagination state if not exists
                if 'rows_per_page' not in st.session_state:
                    st.session_state.rows_per_page = 20
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 1
                
                # Calculate pagination
                total_pages = len(df_sorted) // st.session_state.rows_per_page + (1 if len(df_sorted) % st.session_state.rows_per_page > 0 else 0)
                page = min(st.session_state.current_page, total_pages)
                start_idx = (page - 1) * st.session_state.rows_per_page
                end_idx = min(start_idx + st.session_state.rows_per_page, len(df_sorted))
                
                # Display page information
                st.write(f"Showing {start_idx + 1} to {end_idx} of {len(df_sorted)} entries")
                
                # Display the paginated dataframe
                st.dataframe(
                    df_sorted.iloc[start_idx:end_idx],
                    use_container_width=True
                )
                
                # Controls section
                st.write("---")
                st.write("Table Controls")
                
                # Create three columns for controls
                page_col, rows_col, spacer = st.columns([2, 2, 1])
                
                with rows_col:
                    new_rows_per_page = st.selectbox(
                        "Rows per page",
                        options=[10, 20, 50, 100],
                        index=[10, 20, 50, 100].index(st.session_state.rows_per_page)
                    )
                    if new_rows_per_page != st.session_state.rows_per_page:
                        st.session_state.rows_per_page = new_rows_per_page
                        st.session_state.current_page = 1
                        st.rerun()
                
                with page_col:
                    new_page = st.number_input(
                        "Page",
                        min_value=1,
                        max_value=total_pages,
                        value=page
                    )
                    if new_page != st.session_state.current_page:
                        st.session_state.current_page = new_page
                        st.rerun()
                
                # Sorting options
                st.write("---")
                st.write("Sort Options")
                sort_col, sort_order = st.columns([2, 2])
                
                with sort_col:
                    sort_by = st.selectbox(
                        "Sort by",
                        options=['search_date'] + [col for col in df.columns if col != 'search_date'],
                        index=0
                    )
                
                with sort_order:
                    ascending = st.selectbox(
                        "Order",
                        options=['Newest First', 'Oldest First'],
                        index=0
                    ) == 'Oldest First'
                
                # Re-sort if needed
                if sort_by != 'search_date' or ascending:
                    df_sorted = df.sort_values(by=sort_by, ascending=ascending)
                    st.rerun()
                
                # Export button
                st.write("---")
                if st.button("Export Results", type="secondary"):
                    # Create a CSV in memory
                    csv = df_sorted.to_csv(index=False)
                    # Provide download button
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"search_history_{self.current_client}.csv",
                        mime="text/csv",
                        type="secondary"
                    )
            else:
                st.info("No search results available. Run some searches to see results here.")

    def verify_password(self, username, password):
        """Verify if entered password matches stored hash"""
        stored_hash = self.config['credentials']['usernames'][username]['password']
        hasher = stauth.Hasher()
        entered_hash = hasher.hash(password)
        return stored_hash == entered_hash

    def check_password_complexity(self, password):
        """Check if password meets complexity requirements"""
        checks = {
            'length': len(password) >= 10,
            'uppercase': any(c.isupper() for c in password),
            'lowercase': any(c.islower() for c in password),
            'symbol': any(not c.isalnum() for c in password)
        }
        return checks

    def display_password_requirements(self, checks):
        """Display password requirements status"""
        st.markdown("Password requirements:")
        for req, met in checks.items():
            icon = "✅" if met else "❌"
            if req == 'length':
                st.markdown(f"{icon} Minimum 10 characters")
            elif req == 'uppercase':
                st.markdown(f"{icon} At least 1 uppercase letter")
            elif req == 'lowercase':
                st.markdown(f"{icon} At least 1 lowercase letter")
            elif req == 'symbol':
                st.markdown(f"{icon} At least 1 special character")

    def user_profile_section(self):
        """User profile management section"""
        with st.sidebar.expander("👤 User Profile", expanded=False):
            if st.session_state["authentication_status"]:
                user_info = self.config['credentials']['usernames'][self.username]
                
                st.write(f"**Current User:** {user_info['name']}")
                st.write(f"**Role:** {user_info.get('role', 'user')}")
                
                new_name = st.text_input("Name", value=user_info['name'])
                new_email = st.text_input("Email", value=user_info['email'])
                
                if st.button("Update Profile"):
                    # Update profile in config
                    self.config['credentials']['usernames'][self.username]['name'] = new_name
                    self.config['credentials']['usernames'][self.username]['email'] = new_email
                    
                    # Save updated config
                    with open('config_login.yaml', 'w') as file:
                        yaml.dump(self.config, file, default_flow_style=False)
                    
                    st.success("Profile updated successfully!")
                
                # Reset Password Section
                st.markdown("---")
                col1, col2 = st.columns([1, 3])
                show_password = col1.checkbox("Change Password", value=False)
                if show_password:
                    try:
                        if self.authenticator.reset_password(
                            username=st.session_state["username"],
                            location="sidebar",
                            key="reset_password"
                        ):
                            st.success("Password modified successfully")
                            # Save the updated config
                            with open('config_login.yaml', 'w') as file:
                                yaml.dump(self.config, file, default_flow_style=False)
                    except Exception as e:
                        st.error(e)
            
            # Forgot Password functionality for non-authenticated users
            elif not st.session_state.get("authentication_status"):
                with st.expander("Forgot Password?"):
                    reset_email = st.text_input("Enter your email")
                    if st.button("Reset Password"):
                        # Find user with matching email
                        user_found = False
                        for username, user_data in self.config['credentials']['usernames'].items():
                            if user_data['email'] == reset_email:
                                user_found = True
                                # In a real application, you would:
                                # 1. Generate a secure reset token
                                # 2. Send reset email
                                # 3. Create a reset page
                                break
                        
                        if not user_found:
                            # Don't indicate if email wasn't found (security best practice)
                            st.info("If an account exists with this email, you will receive reset instructions.")
            
    def get_initial_client(self):
        """Get the initial client from config based on username"""
        if not self.username:
            return None
            
        user_info = self.config['credentials']['usernames'][self.username]
        client = user_info.get('client')
        
        if isinstance(client, list):  # Admin with list of clients
            return client[0] if client else None
        return client  # Regular user with single client

    def run(self):
        """Main method to run the application"""
        # Add title in main area
        st.title("agentico.ai : Leads Funnel Manager")
        
        # Authentication
        self.authenticator.login(location="sidebar")
        
        # Debug information
        # st.sidebar.write("Debug Info:")
        # st.sidebar.write(f"Auth Status: {st.session_state.get('authentication_status')}")
        # st.sidebar.write(f"Session State: {st.session_state}")

        if st.session_state["authentication_status"]:
            self.authenticator.logout(location="sidebar")
            st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
                       
            # Get authenticated user info
            self.username = st.session_state["username"]
            
            # Load initial client from config
            if not self.current_client:
                self.current_client = self.get_initial_client()
            
            # Display client selector
            selected_client = self.client_selector()
            
            # Display user profile section
            self.user_profile_section()
            
            if selected_client:
                self.upload_contacts_section()
                self.search_strategy_section()
                self.execute_searches_section()
                self.extract_links_section()
                self.score_potential_section()
                self.assess_novelty_section()
                self.rank_prospects_section()
                self.compose_communications_section()
                self.results_section()
            else:
                st.error("No client folder available")
                
        elif st.session_state["authentication_status"] is False:
            st.error('Username/password is incorrect')
        else:  # authentication_status is None
            st.warning('Please enter your username and password')
            
if __name__ == "__main__":
    app = LeadFunnelManagerUI()
    app.run()
