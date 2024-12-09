FROM python:3.12-slim  
  
# Set the working directory  
WORKDIR /app  
  
# Copy requirements and install them  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
  
# Copy the application code  
COPY . .  
  
# Expose the port  
EXPOSE 80  
  
# Command to run the application  
CMD ["uvicorn", "your_module_name:app", "--host", "0.0.0.0", "--port", "80"]  