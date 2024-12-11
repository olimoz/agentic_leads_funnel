"""
Storage Manager module for handling file operations in both local and cloud environments.
"""

import os
import logging
from pathlib import Path
from azure.storage.blob import BlobServiceClient
import pandas as pd
import io
from typing import Union

#======================================================================================
# Storage Manager
#======================================================================================

class StorageManager:
    """
    Manages file operations for both local and cloud (Azure Blob Storage) environments.
    Local tends to be DEV, cloud tends to be PROD
    Handles bootstrapping configuration loading and uses a working directory for local operations.
    """

    def __init__(self, app):
        """
        Initialize the StorageManager with minimal bootstrap configuration.
        Defaults to DEV environment.

        Args:
            working_directory (str, optional): The working directory to use for file operations.
        """
        self.app = app
        self.environment = os.environ.get('ENVIRONMENT')
        # print(""Environment = {self.environment}") 
        self.config = self._load_bootstrap_config()
        
        if self.environment == 'PROD':
            connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            if not connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is not set")
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            self.container_name = self.config.get('AZURE_CONTAINER_NAME', 'webresearchapp')
            self.working_directory = "."
            # print(""Operating in PROD environment, container = {self.container_name}")

        else:
            self.working_directory = self._get_working_directory(self.app.working_directory)
            # print(""Operating in DEV environment, working directory = {self.working_directory}")

    def _load_bootstrap_config(self):
        """
        Load minimal bootstrap configuration from environment variables or default values.

        Note:
            The AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME are not provided here
            So, in PROD they must be environment variables else the app won't work
            Whereas in DEV, they are not required, as DEV assumes local PC.
        """
        bootstrap_config = {
            'CONFIG_FILE_NAME': os.environ.get('CONFIG_FILE_NAME', 'config.yaml')
        }
        return bootstrap_config

    def _get_working_directory(self, working_directory=None):
        """
        Determine the working directory for local file operations.
        
        Args:
            working_directory (str, optional): The working directory to use.
        
        Returns:
            Path: The working directory to use for file operations.
        """
        if working_directory:
            return Path(working_directory).resolve()
        
        # First, try to get the function directory (for Azure Functions)
        function_dir = os.environ.get('FUNCTION_DIRECTORY')
        if function_dir:
            return Path(function_dir)
        
        # If not in Azure Functions, use the directory of the current file
        return Path(__file__).parent.parent.absolute()

    def set_working_directory(self, working_directory):
        """
        Set a new working directory for file operations.
        
        Args:
            working_directory (str): The new working directory to use.
        """
        if self.environment != 'PROD':
            self.working_directory = self._get_working_directory(working_directory)
        else:
            logging.warning("Setting working directory has no effect in PROD environment")

    def get_file_path(self, file_path, client=None):
        """
        Get the full file path for either local or cloud storage.
        If client is provided, ensures path always includes 'clients/client_name' structure.

        Args:
            file_path (str): The filename (e.g., 'test.xlsx')
            client (str, optional): The client name or path. If a path is provided, 
                                the last component is used as the client name.

        Returns:
            str: The full file path, ensuring client paths include 'clients/client_name'
        """
        path = Path(file_path)
        
        if client:
            # Extract just the client name from any provided path
            client_name = Path(client).name
            # Always construct as clients/client_name
            client_path = Path('clients') / client_name
        else:
            client_path = Path('')

        if self.environment == 'PROD':
            # For PROD, we always treat the path as relative to the container
            return str(client_path / path)
        else:
            # For non-PROD environments
            if path.is_absolute():
                return str(path.parent / client_path / path.name) if client else str(path)
            else:
                return str(self.working_directory / client_path / path)

    def read_file(self, file_path, client=None):
        """
        Read the contents of a file.

        Args:
            file_path (str): The relative path of the file to read.
            client (str, optional): The client name, used as a subfolder.

        Returns:
            Union[str, bytes, None]: The contents of the file as string or bytes, or None if an error occurred.
        """
        full_path = self.get_file_path(file_path, client)
        
        # Determine if the file should be read as binary based on extension
        is_binary = any(full_path.lower().endswith(ext) for ext in [
            '.doc', '.docx', '.pdf', '.xlsx', '.xls', '.zip', '.png', '.jpg', '.jpeg'
        ])

        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name, 
                    blob=full_path
                )
                
                if is_binary:
                    # For binary files, download directly as bytes
                    return blob_client.download_blob().readall()
                else:
                    # For text files, download as text
                    download_stream = blob_client.download_blob()
                    return download_stream.content_as_text(encoding='utf-8')
            else:
                # Local file system handling
                if is_binary:
                    with open(full_path, 'rb') as file:
                        return file.read()
                else:
                    with open(full_path, 'r', encoding='utf-8') as file:
                        return file.read()
                        
        except Exception as e:
            self.app.handle_error(
                self.app.logger, 
                logging.ERROR, 
                f"Error reading file {full_path}: {str(e)}"
            )
        return None

    def write_file_binary(self, content, file_path, client=None):
        """
        Write binary content to a file.

        Args:
            content (bytes): The binary content to write to the file.
            file_path (str): The relative path of the file to write.
            client (str, optional): The client name, used as a subfolder.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                blob_client.upload_blob(content, overwrite=True)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as file:  # Note the 'wb' mode for binary writing
                    file.write(content)
        except Exception as e:
            self.app.handle_error(self.app.logger, logging.CRITICAL, f"Error writing file {full_path}: {str(e)}")
            raise

    def write_file(self, content, file_path, client=None):
        """
        Write content to a file.

        Args:
            file_path (str): The relative path of the file to write.
            content (str): The content to write to the file.
            client (str, optional): The client name, used as a subfolder.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                blob_client.upload_blob(content, overwrite=True)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as file:
                    file.write(content)
        except Exception as e:
            self.app.handle_error(self.app.logger, logging.CRITICAL, f"Error writing file {full_path}: {str(e)}")
            raise

    def append_to_file(self, content, file_path, client=None):
        """"Appending to files, especailly used for the logger"""
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                if blob_client.exists():
                    existing_content = blob_client.download_blob().readall().decode('utf-8')
                    content = existing_content + content
                blob_client.upload_blob(content, overwrite=True)
            else:
                with open(full_path, 'a') as file:
                    file.write(content)
        except Exception as e:
            self.app.handle_error(self.app.logger, logging.CRITICAL, f"Error appending file {full_path}: {str(e)}")

    def file_exists(self, file_path, client=None):
        """
        Check if a file exists.

        Args:
            file_path (str): The relative path of the file to check.
            client (str, optional): The client name, used as a subfolder.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                return blob_client.exists()
            else:
                return Path(full_path).exists()
        except Exception as e:
            msg = f"Error checking file existence {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def list_files(self, directory, client=None):
        """
        List all files in a directory.

        Args:
            directory (str): The relative path of the directory to list.
            client (str, optional): The client name, used as a subfolder.

        Returns:
            List[str]: A list of file paths in the directory.
        """
        full_path = self.get_file_path(directory, client)
        try:
            if self.environment == 'PROD':
                container_client = self.blob_service_client.get_container_client(self.container_name)
                return [blob.name for blob in container_client.list_blobs(name_starts_with=full_path)]
            else:
                return [str(f.relative_to(self.local_base_path)) for f in Path(full_path).glob('**/*') if f.is_file()]
        except Exception as e:
            msg = f"Error listing files in directory {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def read_excel(self, file_path, client=None, **kwargs):
        """
        Read an Excel file and return it as a pandas DataFrame.

        Args:
            file_path (str): The relative path of the Excel file to read.
            client (str, optional): The client name, used as a subfolder.
            **kwargs: Additional keyword arguments to pass to pd.read_excel().

        Returns:
            pd.DataFrame: The contents of the Excel file as a DataFrame.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                stream = blob_client.download_blob()
                return pd.read_excel(io.BytesIO(stream.readall()), **kwargs)
            else:
                return pd.read_excel(full_path, **kwargs)
        except Exception as e:
            msg = f"Error reading Excel file {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def to_excel(self, df, file_path, client=None, **kwargs):
        """
        Write a pandas DataFrame to an Excel file.

        Args:
            file_path (str): The relative path of the Excel file to write.
            df (pd.DataFrame): The DataFrame to write to the Excel file.
            client (str, optional): The client name, used as a subfolder.
            **kwargs: Additional keyword arguments to pass to df.to_excel().
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, **kwargs)
                buffer.seek(0)
                
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                blob_client.upload_blob(buffer.getvalue(), overwrite=True)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                df.to_excel(full_path, **kwargs)
        except Exception as e:
            msg = f"Error writing Excel file {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def read_parquet(self, file_path, client=None):
        """
        Read a Parquet file and return it as a pandas DataFrame.

        Args:
            file_path (str): The relative path of the Parquet file to read.
            client (str, optional): The client name, used as a subfolder.

        Returns:
            pd.DataFrame: The contents of the Parquet file as a DataFrame.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                stream = blob_client.download_blob()
                return pd.read_parquet(io.BytesIO(stream.readall()))
            else:
                return pd.read_parquet(full_path)
        except Exception as e:
            msg = f"Error reading Parquet file {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def to_parquet(self, df, file_path, client=None):
        """
        Write a pandas DataFrame to a Parquet file.

        Args:
            file_path (str): The relative path of the Parquet file to write.
            df (pd.DataFrame): The DataFrame to write to the Parquet file.
            client (str, optional): The client name, used as a subfolder.
        """
        full_path = self.get_file_path(file_path, client)
        try:
            if self.environment == 'PROD':
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=full_path)
                buffer = io.BytesIO()
                df.to_parquet(buffer)
                buffer.seek(0)
                blob_client.upload_blob(buffer.getvalue(), overwrite=True)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                df.to_parquet(full_path)
        except Exception as e:
            msg = f"Error writing Parquet file {full_path}: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
            raise

    def append_to_parquet(self, df, file_path, client=None):
        """
        Append a pandas DataFrame to an existing Parquet file or create a new one if it doesn't exist.

        This method handles both cases where the file already exists and needs to be appended to,
        and where the file doesn't exist and needs to be created. It also ensures that the schema
        of the existing file (if any) matches the schema of the new data being appended.

        Args:
            file_path (str): The relative path of the Parquet file.
            df (pd.DataFrame): The DataFrame to append to the Parquet file.
            client (str, optional): The client name, used as a subfolder.

        Raises:
            ValueError: If the schema of the existing file doesn't match the new data.
        """
        full_path = self.get_file_path(file_path, client)
        
        try:
            # Try to open existing parquet file
            existing_df = self.read_parquet(full_path, client)
            filenotfound = False
        except FileNotFoundError:
            # If file doesn't exist, use the new dataframe
            filenotfound = True
            combined_df = df

        # If we loaded from file, then ensure column counts of df and existing_df are the same
        if not filenotfound:
            if df.shape[1] != existing_df.shape[1]:
                msg = f"Cannot concatenate df to {full_path}. Column count not same: {df.shape} vs {existing_df.shape}"
                print(msg)
                self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
                return
            else:
                # ensure column types are the same, the dataframe from file is the master
                for col in df.columns:
                    if df[col].dtype != existing_df[col].dtype:
                        self.app.logger.info(f"Converting {col} in df to {existing_df[col].dtype} to match {full_path}")
                        df[col] = df[col].astype(existing_df[col].dtype)

                # concatenate the dataframes
                combined_df = pd.concat([existing_df, df], ignore_index=True)

        # Write the combined dataframe to parquet
        self.to_parquet(combined_df, full_path, client)

    def get_file_modification_time(self, file_path):
        """
        Get the modification time of a file.

        Args:
            file_path (str): The path of the file.

        Returns:
            float: The modification time of the file as a timestamp.
        """
        if self.environment == 'PROD':
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_path)
            properties = blob_client.get_blob_properties()
            return properties.last_modified.timestamp()
        else:
            return os.path.getmtime(self.get_file_path(file_path))

    def delete_file(self, file_path):
        """
        Delete a file.

        Args:
            file_path (str): The path of the file to delete.
        """
        if self.environment == 'PROD':
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_path)
            blob_client.delete_blob()
        else:
            os.remove(self.get_file_path(file_path))
