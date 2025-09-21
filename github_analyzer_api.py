#!/usr/bin/env python3
"""
GitHub Repository Analyzer API Module

This module handles all GitHub API interactions for the repository analyzer.
"""

import os
import requests
import base64
from urllib.parse import urlparse
import time
from collections import defaultdict
import re

class GitHubAPIAnalyzer:
    """Class for analyzing GitHub repositories using the GitHub API."""
    
    def __init__(self, repo_url, github_token=None):
        """
        Initialize the analyzer with repository URL and GitHub token.
        
        Args:
            repo_url (str): URL of the GitHub repository
            github_token (str, optional): GitHub API token for authenticated requests
        """
        self.repo_url = repo_url
        self.github_token = github_token
        
        # Parse repository information from URL
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
            
        self.owner = path_parts[0]
        self.repo_name = path_parts[1]
        
        # Set up API headers
        self.headers = {}
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        # Initialize data structures
        self.repo_info = {}
        self.file_count = 0
        self.language_stats = {}
        self.functions = []
        self.classes = []
        self.readme_content = ""
        self.repo_structure = {}
        self.rate_limit_remaining = 0
        
    def _make_api_request(self, url, params=None):
        """
        Make a request to the GitHub API with rate limit handling.
        
        Args:
            url (str): API endpoint URL
            params (dict, optional): Query parameters
            
        Returns:
            dict: JSON response or None if request failed
        """
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            
            # Handle rate limiting
            if response.status_code == 403 and self.rate_limit_remaining == 0:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                sleep_time = max(0, reset_time - time.time()) + 1
                print(f"Rate limit exceeded. Waiting for {sleep_time:.0f} seconds...")
                time.sleep(sleep_time)
                return self._make_api_request(url, params)
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None
    
    def fetch_repo_info(self):
        """
        Fetch basic repository information.
        
        Returns:
            dict: Repository information
        """
        print("Fetching repository information...")
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
        self.repo_info = self._make_api_request(api_url) or {}
        return self.repo_info
    
    def fetch_languages(self):
        """
        Fetch language statistics for the repository.
        
        Returns:
            dict: Language statistics
        """
        print("Fetching language statistics...")
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/languages"
        self.language_stats = self._make_api_request(api_url) or {}
        return self.language_stats
    
    def fetch_readme(self):
        """
        Fetch repository README content.
        
        Returns:
            str: README content or empty string if not found
        """
        print("Fetching README content...")
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/readme"
        readme_data = self._make_api_request(api_url)
        
        if readme_data and 'content' in readme_data:
            try:
                content = base64.b64decode(readme_data['content']).decode('utf-8')
                self.readme_content = content
                return content
            except Exception as e:
                print(f"Error decoding README: {e}")
        
        return ""
        
    def generate_readme(self, analysis_results):
        """
        Generate a README file for repositories that don't have one.
        
        Args:
            analysis_results (dict): Results from repository analysis
            
        Returns:
            str: Generated README content
        """
        print("Generating README content...")
        
        repo_info = self.repo_info
        language_stats = analysis_results.get('language_stats', {})
        features = analysis_results.get('features', [])
        functions = analysis_results.get('functions', [])
        classes = analysis_results.get('classes', [])
        
        # Start with repository name and description
        readme = f"# {repo_info.get('name', self.repo_name)}\n\n"
        
        if repo_info.get('description'):
            readme += f"{repo_info.get('description')}\n\n"
        else:
            readme += "A GitHub repository.\n\n"
        
        # Add badges for stars, forks, etc.
        readme += f"![GitHub stars](https://img.shields.io/github/stars/{self.owner}/{self.repo_name}?style=social) "
        readme += f"![GitHub forks](https://img.shields.io/github/forks/{self.owner}/{self.repo_name}?style=social) "
        readme += f"![GitHub watchers](https://img.shields.io/github/watchers/{self.owner}/{self.repo_name}?style=social)\n\n"
        
        # Add repository overview
        readme += "## Overview\n\n"
        readme += f"This repository is maintained by [{self.owner}](https://github.com/{self.owner}) "
        
        if repo_info.get('license') and repo_info.get('license').get('name'):
            readme += f"and is licensed under {repo_info.get('license').get('name')}.\n\n"
        else:
            readme += "and does not specify a license.\n\n"
        
        # Add language information
        if language_stats:
            readme += "## Languages\n\n"
            total_bytes = sum(language_stats.values())
            
            for lang, bytes_count in sorted(language_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                readme += f"- **{lang}**: {percentage:.1f}%\n"
            
            readme += "\n"
        
        # Add detected features and technologies
        if features:
            readme += "## Technologies\n\n"
            for feature in sorted(features):
                readme += f"- {feature}\n"
            readme += "\n"
        
        # Add installation section
        readme += "## Installation\n\n"
        readme += "```bash\n"
        readme += f"git clone https://github.com/{self.owner}/{self.repo_name}.git\n"
        readme += f"cd {self.repo_name}\n"
        
        # Add language-specific installation instructions
        if "Python" in features or ".py" in language_stats:
            readme += "pip install -r requirements.txt  # If available\n"
        elif "JavaScript" in features or "TypeScript" in features or ".js" in language_stats or ".ts" in language_stats:
            readme += "npm install  # If available\n"
        elif "Java" in features or ".java" in language_stats:
            readme += "./gradlew build  # For Gradle projects\n"
            readme += "# OR\n"
            readme += "mvn install  # For Maven projects\n"
        
        readme += "```\n\n"
        
        # Add usage section
        readme += "## Usage\n\n"
        readme += "Please refer to the documentation or code examples for usage instructions.\n\n"
        
        # Add structure section
        readme += "## Project Structure\n\n"
        readme += "```\n"
        
        def print_structure(structure, prefix="", is_last=True):
            result = ""
            keys = list(structure.keys())
            keys = [k for k in keys if k != "__files"]
            
            # Print files first
            if "__files" in structure:
                for i, file in enumerate(sorted(structure["__files"])):
                    is_file_last = (i == len(structure["__files"]) - 1) and not keys
                    result += f"{prefix}{'└── ' if is_file_last else '├── '}{file}\n"
            
            # Then print directories
            for i, key in enumerate(sorted(keys)):
                is_dir_last = i == len(keys) - 1
                result += f"{prefix}{'└── ' if is_dir_last else '├── '}{key}/\n"
                result += print_structure(
                    structure[key], 
                    prefix + ("    " if is_dir_last else "│   "), 
                    is_dir_last
                )
            return result
        
        readme += print_structure(analysis_results.get('repo_structure', {}))
        readme += "```\n\n"
        
        # Add key functions section if available
        if functions:
            readme += "## Key Functions\n\n"
            
            # Group functions by language
            functions_by_language = {}
            for func in functions[:20]:  # Limit to 20 functions
                lang = func.get('language', 'Unknown')
                if lang not in functions_by_language:
                    functions_by_language[lang] = []
                functions_by_language[lang].append(func)
            
            for lang, funcs in functions_by_language.items():
                readme += f"### {lang}\n\n"
                for func in funcs[:5]:  # Show top 5 per language
                    readme += f"- `{func.get('name')}({func.get('params')})`\n"
                readme += "\n"
        
        # Add key classes section if available
        if classes:
            readme += "## Key Classes\n\n"
            
            # Group classes by language
            classes_by_language = {}
            for cls in classes[:20]:  # Limit to 20 classes
                lang = cls.get('language', 'Unknown')
                if lang not in classes_by_language:
                    classes_by_language[lang] = []
                classes_by_language[lang].append(cls)
            
            for lang, cls_list in classes_by_language.items():
                readme += f"### {lang}\n\n"
                for cls in cls_list[:5]:  # Show top 5 per language
                    inheritance = f" extends {cls.get('inheritance')}" if cls.get('inheritance') else ""
                    readme += f"- `{cls.get('name')}{inheritance}`\n"
                readme += "\n"
        
        # Add contributing section
        readme += "## Contributing\n\n"
        readme += "Contributions are welcome! Please feel free to submit a Pull Request.\n\n"
        
        # Add license section
        if repo_info.get('license') and repo_info.get('license').get('name'):
            readme += "## License\n\n"
            readme += f"This project is licensed under the {repo_info.get('license').get('name')}.\n"
        
        # Add note about auto-generation
        readme += "\n---\n\n"
        readme += "*This README was automatically generated by GitHub Repository Analyzer.*\n"
        
        return readme
    
    def fetch_directory_contents(self, path=""):
        """
        Recursively fetch directory contents.
        
        Args:
            path (str): Directory path within the repository
            
        Returns:
            dict: Directory structure
        """
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/contents/{path}"
        contents = self._make_api_request(api_url)
        
        if not contents or not isinstance(contents, list):
            return {}
        
        result = {}
        for item in contents:
            if item['name'].startswith('.') or item['name'] in ['node_modules', '__pycache__']:
                continue
                
            if item['type'] == 'dir':
                result[item['name']] = self.fetch_directory_contents(item['path'])
            else:
                if '__files' not in result:
                    result['__files'] = []
                result['__files'].append(item['name'])
                self.file_count += 1
                
                # Analyze file content if it's a code file
                if self._is_code_file(item['name']):
                    self._analyze_file_content(item)
        
        return result
    
    def _is_code_file(self, filename):
        """
        Check if a file is a code file that should be analyzed.
        
        Args:
            filename (str): Name of the file
            
        Returns:
            bool: True if the file should be analyzed
        """
        _, ext = os.path.splitext(filename.lower())
        return ext in ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rb', '.php', '.ts', '.jsx', '.tsx', '.kt', '.kts']
    
    def _analyze_file_content(self, file_info):
        """
        Analyze the content of a code file.
        
        Args:
            file_info (dict): File information from GitHub API
        """
        if file_info.get('size', 0) > 500000:  # Skip files larger than 500KB
            return
            
        content_url = file_info.get('download_url')
        if not content_url:
            return
            
        try:
            response = requests.get(content_url, headers=self.headers)
            response.raise_for_status()
            content = response.text
            
            # Extract functions and classes based on file extension
            _, ext = os.path.splitext(file_info['name'].lower())
            path = file_info.get('path', '')
            
            if ext == '.py':
                self._extract_python_elements(content, path)
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                self._extract_js_elements(content, path)
            elif ext in ['.java']:
                self._extract_java_elements(content, path)
            elif ext in ['.kt', '.kts']:
                self._extract_kotlin_elements(content, path)
                
        except Exception as e:
            print(f"Error analyzing file {file_info.get('path')}: {e}")
    
    def _extract_python_elements(self, content, file_path):
        """Extract functions and classes from Python code."""
        # Find function definitions
        func_matches = re.finditer(r'def\s+([a-zA-Z0-9_]+)\s*\((.*?)\):', content)
        for match in func_matches:
            func_name = match.group(1)
            params = match.group(2)
            
            # Skip private functions
            if func_name.startswith('_') and not func_name.startswith('__'):
                continue
                
            self.functions.append({
                'name': func_name,
                'file': file_path,
                'params': params,
                'language': 'Python'
            })
            
        # Find class definitions
        class_matches = re.finditer(r'class\s+([a-zA-Z0-9_]+)(?:\((.*?)\))?:', content)
        for match in class_matches:
            class_name = match.group(1)
            inheritance = match.group(2) if match.group(2) else ""
            
            self.classes.append({
                'name': class_name,
                'file': file_path,
                'inheritance': inheritance,
                'language': 'Python'
            })
    
    def _extract_js_elements(self, content, file_path):
        """Extract functions and classes from JavaScript/TypeScript code."""
        # Find function declarations
        func_matches = re.finditer(r'function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', content)
        for match in func_matches:
            self.functions.append({
                'name': match.group(1),
                'file': file_path,
                'params': match.group(2),
                'language': 'JavaScript'
            })
            
        # Find arrow functions with names (const x = () => {})
        arrow_func_matches = re.finditer(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:\(.*?\)|[a-zA-Z0-9_]+)\s*=>', content)
        for match in arrow_func_matches:
            self.functions.append({
                'name': match.group(1),
                'file': file_path,
                'params': 'arrow function',
                'language': 'JavaScript'
            })
            
        # Find ES6 class declarations
        class_matches = re.finditer(r'class\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_]+))?', content)
        for match in class_matches:
            self.classes.append({
                'name': match.group(1),
                'file': file_path,
                'inheritance': match.group(2) if match.group(2) else "",
                'language': 'JavaScript'
            })
    
    def _extract_java_elements(self, content, file_path):
        """Extract functions and classes from Java code."""
        # Find class definitions
        class_matches = re.finditer(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_]+))?(?:\s+implements\s+([a-zA-Z0-9_, ]+))?', content)
        for match in class_matches:
            class_name = match.group(1)
            inheritance = match.group(2) if match.group(2) else ""
            
            self.classes.append({
                'name': class_name,
                'file': file_path,
                'inheritance': inheritance,
                'language': 'Java'
            })
            
        # Find method definitions
        method_matches = re.finditer(r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:[a-zA-Z0-9_<>[\],\s]+)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', content)
        for match in method_matches:
            method_name = match.group(1)
            params = match.group(2)
            
            self.functions.append({
                'name': method_name,
                'file': file_path,
                'params': params,
                'language': 'Java'
            })
            
    def _extract_kotlin_elements(self, content, file_path):
        """Extract functions and classes from Kotlin code."""
        # Find class definitions
        class_matches = re.finditer(r'(?:open|abstract|sealed|final|)?\s*(?:class|interface|object)\s+([a-zA-Z0-9_]+)(?:\s*(?:<.*?>)?(?:\s*:\s*([a-zA-Z0-9_<>, ]+))?)?', content, re.MULTILINE)
        for match in class_matches:
            class_name = match.group(1)
            inheritance = match.group(2) if match.group(2) else ""
            
            self.classes.append({
                'name': class_name,
                'file': file_path,
                'inheritance': inheritance,
                'language': 'Kotlin'
            })
            
        # Find function definitions
        func_matches = re.finditer(r'(?:private|public|internal|protected|)?\s*(?:suspend|inline|)?\s*fun\s+(?:<.*?>)?\s*(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)\s*(?:<.*?>)?\s*\((.*?)\)(?:\s*:\s*[a-zA-Z0-9_<>., ]+)?', content, re.MULTILINE | re.DOTALL)
        for match in func_matches:
            func_name = match.group(1)
            params = match.group(2)
            
            # Skip private functions if needed
            if func_name.startswith('_') and not func_name.startswith('__'):
                continue
                
            self.functions.append({
                'name': func_name,
                'file': file_path,
                'params': params,
                'language': 'Kotlin'
            })
            
        # Find extension functions
        extension_func_matches = re.finditer(r'(?:private|public|internal|protected|)?\s*(?:suspend|inline|)?\s*fun\s+([a-zA-Z0-9_<>., ]+)\.([a-zA-Z0-9_]+)\s*\((.*?)\)(?:\s*:\s*[a-zA-Z0-9_<>., ]+)?', content, re.MULTILINE | re.DOTALL)
        for match in extension_func_matches:
            receiver_type = match.group(1)
            func_name = match.group(2)
            params = match.group(3)
            
            self.functions.append({
                'name': f"{receiver_type}.{func_name}",
                'file': file_path,
                'params': params,
                'language': 'Kotlin (Extension)'
            })


    def extract_features(self):
        """
        Extract features from the repository.
        
        Returns:
            list: Detected features
        """
        features = []
        
        # Add language-based features
        for lang in self.language_stats.keys():
            features.append(lang)
        
        # Check for common frameworks based on repository structure
        if self.repo_structure:
            frameworks = {
                'Django': ['django', 'settings.py', 'wsgi.py'],
                'Flask': ['app.py', 'flask', 'routes.py'],
                'React': ['react', 'jsx', 'components'],
                'Angular': ['angular.json', 'component.ts'],
                'Vue.js': ['vue.config.js', '.vue'],
                'Express.js': ['express', 'routes', 'app.js'],
                'Spring Boot': ['application.properties', 'SpringApplication'],
                'Docker': ['Dockerfile', 'docker-compose.yml'],
                'Kubernetes': ['k8s', 'deployment.yaml'],
                'Next.js': ['next.config.js', 'pages'],
                'GraphQL': ['graphql', 'schema.graphql'],
                'TypeScript': ['tsconfig.json', '.ts'],
                'Jest': ['jest.config.js', 'test.js'],
                'Pytest': ['pytest.ini', 'test_'],
            }
            
            # Convert structure to string for easier searching
            structure_str = str(self.repo_structure)
            
            for framework, indicators in frameworks.items():
                for indicator in indicators:
                    if indicator.lower() in structure_str.lower():
                        features.append(framework)
                        break
        
        # Remove duplicates
        return list(set(features))
    
    def analyze(self):
        """
        Analyze the repository.
        
        Returns:
            dict: Analysis results
        """
        try:
            print(f"Analyzing repository: {self.repo_url}")
            
            # Fetch repository information
            self.fetch_repo_info()
            
            # Fetch language statistics
            self.fetch_languages()
            
            # Fetch README content
            self.fetch_readme()
            
            # Fetch repository structure
            print("Fetching repository structure...")
            self.repo_structure = self.fetch_directory_contents()
            
            # Extract features
            features = self.extract_features()
            
            return {
                'repo_info': self.repo_info,
                'language_stats': self.language_stats,
                'readme_content': self.readme_content,
                'repo_structure': self.repo_structure,
                'functions': self.functions,
                'classes': self.classes,
                'features': features,
                'file_count': self.file_count,
                'has_original_readme': bool(self.readme_content)
            }
            
        except Exception as e:
            print(f"Error analyzing repository: {e}")
            return None
