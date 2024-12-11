# Lead Funnel Manager - Design Requirements

## 1. System Overview
The Lead Funnel Manager is a Streamlit-based application designed to manage and automate the lead generation and qualification process. The system integrates various AI-powered agents to search, analyze, and process potential business leads.

## 2. Core Components

### 2.1 User Interface Requirements
- **Framework**: Streamlit-based web interface
- **Styling**:
  - Custom button styling with alternating colors (#e47c0d and #3c8b97)
  - Expander components with distinctive styling
  - Consistent visual hierarchy and typography
  - Responsive design for various screen sizes

### 2.2 Data Management
- **Client Data Storage**:
  - Support for loading and managing client information
  - Persistent storage of client records
  - Data validation and sanitization

### 2.3 AI Agent Integration
The system must integrate multiple specialized AI agents for:
1. Search Proposal Generation
2. URL Extraction
3. Target Scoring
4. Results Comparison
5. Search Results Ranking
6. Email Generation

### 2.4 Prompt Management
- **Required Prompt Templates**:
  - Search proposal agent prompt
  - URL extraction agent prompt
  - Target score agent prompt
  - Results comparison agent prompt
  - Search results ranking agent prompt
  - Email proposal agent prompt
  - Business description template
  - Email template

## 3. Functional Requirements

### 3.1 Core Features
- User authentication and session management
- Client data management (CRUD operations)
- Lead search and qualification workflow
- Email template generation and customization
- Results visualization and reporting

### 3.2 Workflow Automation
- Automated lead scoring system
- Intelligent search proposal generation
- Automated email content generation
- URL extraction and validation
- Results ranking and prioritization

## 4. Technical Requirements

### 4.1 Dependencies
- Python 3.x
- Streamlit
- Pandas
- Azure Blob Storage integration
- Path handling utilities

### 4.2 Storage Requirements
- Azure Blob Container integration
- Local file system access for templates
- Secure storage for sensitive data

### 4.3 Performance Requirements
- Responsive UI with minimal latency
- Efficient data processing for large datasets
- Optimized AI agent response times

## 5. Security Requirements
- Secure handling of client data
- Protected access to AI agent endpoints
- Safe storage of credentials and sensitive information
- Input validation and sanitization

## 6. Maintenance Requirements
- Modular code structure for easy updates
- Clear documentation of AI agent interfaces
- Version control for prompt templates
- Regular backup procedures

## 7. Future Considerations
- Integration with additional AI services
- Enhanced reporting capabilities
- Advanced lead scoring algorithms
- Multi-user support
- API endpoint exposure for external integration

## 8. User Experience Guidelines
- Intuitive navigation flow
- Clear feedback for user actions
- Consistent error handling
- Progressive disclosure of complex features
- Helpful tooltips and documentation

## 9. File Structure and Locations

### 9.1 Core Application Files
- `/home/oliver/MindSearch/mindsearch/agent/agent_candidate_search/UI/ui.py`: Main UI application
- `/home/oliver/MindSearch/mindsearch/agent/agent_candidate_search/UI/funnel.png`: Funnel visualization image

### 9.2 Data Storage
- `subscriptions.xlsx`: Master list of client subscriptions
- `defaults/`: Default prompt templates
  - `prompt_searchproposalagent.txt`: Default search proposal template
  - `prompt_urlextractionagent.txt`: Default URL extraction template
  - `prompt_targetscoreagent.txt`: Default target scoring template
  - `prompt_resultscomparisonagent.txt`: Default results comparison template
  - `prompt_searchresultsrankingagent.txt`: Default search results ranking template
  - `template_email.md`: Default email template
  - `prompt_businessdescription.md`: Default business description template
  - `prompt_emailproposalagent.txt`: Default email proposal template
- `{client_name}/`: Client-specific directory
  - `df_search_tasks.xlsx`: Client contact list and search tasks
  - Customized versions of all prompt templates

### 9.3 Required DataFrames
1. Client Data (`subscriptions.xlsx`):
   - Required columns: 'client'

2. Contacts DataFrame (`df_search_tasks.xlsx`):
   - Required columns (in order):
     - 'First Name'
     - 'Last Name'
     - 'Company'

### 9.4 Backup Structure
- Automatic backups of contact lists are created as:
  - `{client_name}/df_search_tasks.backup.xlsx`
