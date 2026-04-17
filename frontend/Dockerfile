# Use a standard Python slim image as the base
FROM python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# CORRECTED: Copy the requirements file from its actual location relative to the project root
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CORRECTED: Copy the rest of the frontend application code from its directory
COPY frontend/ .

# Expose the default Streamlit port
EXPOSE 8501

# The command to run the Streamlit app
# --server.address=0.0.0.0 is crucial to allow access from outside the container
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]