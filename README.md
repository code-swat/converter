# PDF Transformer App

An application for PDF transformation into Excel files.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository: 

```bash
git clone https://github.com/code-swat/converter
cd converter
```

2. Create a virtual environment:

```bash
python -m venv .venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Make sure your `.streamlit/secrets.toml` file exists with the following content:

```toml
[connections.sqlite]
url = "sqlite:///database.db"
type = "sql"

[datalab]
api_key = "<your-api-key>"
```

## Running the Application

1. Make sure your virtual environment is activated
2. Run the Streamlit app:
```bash
streamlit run app.py
```

3. Open your browser and navigate to `http://localhost:8501`

## Default Login Credentials

- Username: `admin`
- Password: `admin`

**Note:** For production use, please change the default credentials.

## Development

To add new features or modify existing ones:

1. Database modifications should be made in `config/database.py`
2. New pages should be added to the `pages/` directory
3. Database seeding can be modified in `config/seed.py`

## Security Notes

1. Change the default admin credentials after first login
2. Keep your `.streamlit/secrets.toml` file secure
3. Never commit sensitive information to version control