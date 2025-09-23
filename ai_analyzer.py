#!/usr/bin/env python3
"""
AI-powered GitHub Repository Analyzer

This module uses Google's Generative AI API to analyze repositories and generate README files.
"""

import os
import re
import google.generativeai as genai
from typing import Dict, List, Any, Optional

class AIRepositoryAnalyzer:
    """Class for analyzing repositories using AI."""
    
    def __init__(self, api_key: str):
        """
        Initialize the AI analyzer with the Gemini API key.
        
        Args:
            api_key (str): Google Generative AI API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Get available models
        try:
            models = genai.list_models()
            # Find an appropriate text model
            self.model_name = None
            
            # Print available models for debugging
            print(f"Available models: {[model.name for model in models]}")
            
            # Try to find a suitable Gemini model
            for model in models:
                # First preference: gemini-1.5-pro models (non-vision)
                if "gemini-2.5-flash" in model.name and "vision" not in model.name:
                    self.model_name = model.name
                    break
                # Second preference: any gemini model (non-vision)
                elif "gemini" in model.name and not self.model_name and "vision" not in model.name:
                    self.model_name = model.name
            
            if not self.model_name:
                # Fallback to a specific model from the available list
                self.model_name = "models/gemini-2.5-flash"
                
            print(f"Using AI model: {self.model_name}")
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            print(f"Error initializing AI model: {e}")
            raise



    def analyze_repository(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze repository data using AI.
        
        Args:
            repo_data (dict): Repository data from the GitHub API analyzer
            
        Returns:
            dict: Enhanced repository data with AI insights
        """
        try:
            # Extract key information from repo_data
            repo_name = repo_data.get('repo_info', {}).get('name', 'Unknown Repository')
            repo_description = repo_data.get('repo_info', {}).get('description', '')
            languages = list(repo_data.get('language_stats', {}).keys())
            features = repo_data.get('features', [])
            functions = repo_data.get('functions', [])[:20]  # Limit to 20 functions for prompt size
            classes = repo_data.get('classes', [])[:20]  # Limit to 20 classes for prompt size

            # Create a prompt for the AI
            prompt = self._create_analysis_prompt(
                repo_name, 
                repo_description, 
                languages, 
                features, 
                functions, 
                classes
            )

            print(prompt)
            
            # Get AI response
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            print("response")
            print(response)

            # Parse AI insights
            ai_insights = self._parse_ai_response(response.text)
            
            # Add AI insights to repo_data
            repo_data['ai_insights'] = ai_insights
            
            return repo_data
            
        except Exception as e:
            print(f"Error in AI analysis: {e}")
            # Add fallback insights
            repo_data['ai_insights'] = {
                "project_description": f"A {'/'.join(languages)} repository named {repo_name}.",
                "main_features": features,
                "architecture": "Not identified due to analysis error.",
                "use_cases": ["General purpose application"],
                "technical_highlights": [f"Uses {lang}" for lang in languages[:3]]
            }
            repo_data['ai_error'] = str(e)
            return repo_data
    
    def generate_readme(self, repo_data: Dict[str, Any]) -> str:
        """
        Generate a comprehensive README file using AI.
        
        Args:
            repo_data (dict): Repository data with AI insights
            
        Returns:
            str: Generated README content
        """
        try:
            # Extract key information
            repo_name = repo_data.get('repo_info', {}).get('name', 'Unknown Repository')
            repo_description = repo_data.get('repo_info', {}).get('description', '')
            languages = list(repo_data.get('language_stats', {}).keys())
            features = repo_data.get('features', [])
            ai_insights = repo_data.get('ai_insights', {})
            
            # Create a prompt for README generation
            prompt = self._create_readme_prompt(
                repo_name,
                repo_description,
                languages,
                features,
                ai_insights
            )
            
            # Get AI response
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Return the generated README
            return response.text
            
        except Exception as e:
            print(f"Error in README generation: {e}")
            # Fallback to basic README if AI fails
            return self._generate_basic_readme(repo_data)
    
    def _create_analysis_prompt(
        self, 
        repo_name: str, 
        repo_description: str, 
        languages: List[str], 
        features: List[str], 
        functions: List[Dict[str, str]], 
        classes: List[Dict[str, str]]
    ) -> str:
        """Create a prompt for repository analysis."""
        
        # Format functions and classes for the prompt
        functions_text = "\n".join([
            f"- {func.get('name')}({func.get('params', '')}) in {func.get('file', '')}"
            for func in functions
        ])
        
        classes_text = "\n".join([
            f"- {cls.get('name')} in {cls.get('file', '')}" +
            (f" extends {cls.get('inheritance')}" if cls.get('inheritance') else "")
            for cls in classes
        ])
        
        prompt = f"""
        You are an expert software developer tasked with analyzing a GitHub repository.
        
        Repository Name: {repo_name}
        Repository Description: {repo_description}
        
        Programming Languages: {', '.join(languages)}
        Detected Features/Technologies: {', '.join(features)}
        
        Key Functions:
        {functions_text}
        
        Key Classes:
        {classes_text}
        
        Based on this information, please provide:
        
        1. A concise but comprehensive description of what this project does
        2. The main features and capabilities of this project
        3. The architecture or design pattern being used (if identifiable)
        4. Potential use cases for this project
        5. Any notable technical aspects or interesting implementation details
        
        Format your response as JSON with the following structure:
        {{
            "project_description": "Detailed description of what the project does",
            "main_features": ["Feature 1", "Feature 2", ...],
            "architecture": "Description of the architecture or design pattern",
            "use_cases": ["Use case 1", "Use case 2", ...],
            "technical_highlights": ["Technical aspect 1", "Technical aspect 2", ...]
        }}
        """
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response to extract structured insights."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group(1))
            
            # If no JSON block found, try to parse the entire response as JSON
            import json
            return json.loads(response_text)
            
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Response text: {response_text}...")
            # Return a structured fallback if parsing fails
            return {
                "project_description": "Analysis not available",
                "main_features": [],
                "architecture": "Not identified",
                "use_cases": [],
                "technical_highlights": []
            }
    
    def _create_readme_prompt(
        self, 
        repo_name: str, 
        repo_description: str, 
        languages: List[str], 
        features: List[str], 
        ai_insights: Dict[str, Any]
    ) -> str:
        """Create a prompt for README generation."""
        
        prompt = f"""
        You are an expert technical writer tasked with creating a comprehensive README.md file for a GitHub repository.
        
        Repository Name: {repo_name}
        Repository Description: {repo_description}
        
        Programming Languages: {', '.join(languages)}
        Detected Features/Technologies: {', '.join(features)}
        
        AI Analysis Insights:
        - Project Description: {ai_insights.get('project_description', 'Not available')}
        - Main Features: {', '.join(ai_insights.get('main_features', []))}
        - Architecture: {ai_insights.get('architecture', 'Not identified')}
        - Use Cases: {', '.join(ai_insights.get('use_cases', []))}
        - Technical Highlights: {', '.join(ai_insights.get('technical_highlights', []))}
        
        Please create a complete, professional README.md file that includes:
        
        1. A title and concise description
        2. Badges for the main technologies
        3. Detailed features section
        4. Installation instructions based on the detected technologies
        5. Usage examples with code snippets
        6. API documentation if applicable
        7. Architecture overview
        8. Contributing guidelines
        9. License information
        
        Format your response as a complete Markdown document ready to be used as a README.md file.
        Do not include any explanatory text outside the README content.
        """
        
        return prompt
    
    def _generate_basic_readme(self, repo_data: Dict[str, Any]) -> str:
        """Generate a basic README if AI generation fails."""
        
        repo_name = repo_data.get('repo_info', {}).get('name', 'Unknown Repository')
        repo_description = repo_data.get('repo_info', {}).get('description', '')
        languages = list(repo_data.get('language_stats', {}).keys())
        features = repo_data.get('features', [])
        
        readme = f"# {repo_name}\n\n"
        
        if repo_description:
            readme += f"{repo_description}\n\n"
        
        if languages:
            readme += "## Technologies\n\n"
            for lang in languages:
                readme += f"- {lang}\n"
            readme += "\n"
        
        if features:
            readme += "## Features\n\n"
            for feature in features:
                readme += f"- {feature}\n"
            readme += "\n"
        
        readme += "## Installation\n\n"
        readme += "```bash\n"
        readme += f"git clone https://github.com/username/{repo_name}.git\n"
        readme += f"cd {repo_name}\n"
        readme += "```\n\n"
        
        readme += "## Usage\n\n"
        readme += "Add usage instructions here.\n\n"
        
        readme += "## License\n\n"
        license_name = repo_data.get('repo_info', {}).get('license', {}).get('name', 'Not specified')
        readme += f"This project is licensed under {license_name}.\n"
        
        return readme



    def generate_cURL_Command(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze repository data using AI.

        Args:
            repo_data (dict): Repository data from the GitHub API analyzer

        Returns:
            dict: Enhanced repository data with AI insights
        """
        try:
            # Extract key information from repo_data
            repo_name = repo_data.get('repo_info', {}).get('name', 'Unknown Repository')
            repo_description = repo_data.get('repo_info', {}).get('description', '')
            languages = list(repo_data.get('language_stats', {}).keys())
            features = repo_data.get('features', [])
            functions = repo_data.get('functions', [])[:20]  # Limit to 20 functions for prompt size
            classes = repo_data.get('classes', [])[:20]  # Limit to 20 classes for prompt size

            # Create a prompt for the AI
            prompt = self._create_postman_prompt(
                repo_name,
                repo_description,
                languages,
                features,
                functions,
                classes
            )

            print(prompt)

            # Get AI response
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            print("response")
            print(response.text)

            # # Parse AI insights
            # ai_insights = self._parse_ai_response_postman(response.text)

            # Add AI insights to repo_data
            repo_data['postman'] = response.text

            return repo_data

        except Exception as e:
            print(f"Error in AI analysis: {e}")
            # Add fallback insights
            repo_data['ai_insights'] = {
                "project_description": f"A {'/'.join(languages)} repository named {repo_name}.",
                "main_features": features,
                "architecture": "Not identified due to analysis error.",
                "use_cases": ["General purpose application"],
                "technical_highlights": [f"Uses {lang}" for lang in languages[:3]]
            }
            repo_data['ai_error'] = str(e)
            return repo_data


    def _create_postman_prompt(
            self,
            repo_name: str,
            repo_description: str,
            languages: List[str],
            features: List[str],
            functions: List[Dict[str, str]],
            classes: List[Dict[str, str]]
    ) -> str:

        # Format functions and classes for the prompt
        functions_text = "\n".join([
            f"- {func.get('name')}({func.get('params', '')}) in {func.get('file', '')}"
            for func in functions
        ])

        classes_text = "\n".join([
            f"- {cls.get('name')} in {cls.get('file', '')}" +
            (f" extends {cls.get('inheritance')}" if cls.get('inheritance') else "")
            for cls in classes
        ])

        prompt = f"""
        You are an expert software developer tasked with creating curl commands from Controller classes.
        
        Repository Name: {repo_name}
        Repository Description: {repo_description}
        
        Programming Languages: {', '.join(languages)}
        Detected Features/Technologies: {', '.join(features)}
        
        Key Functions:
        {functions_text}
        
        Key Classes:
        {classes_text}
        
        Based on this information, please analyze:
        1. The controller classes and create curl command for each endpoint.
        2. Parse the annotations (@RequestMapping, @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping) for each controller class for better understanding.
        3. Avoid relying on any prior assumptions or cached information once a specific file path is given.
        4. Make sure you just return curl commands as multi line string, nothing extra to be returned
        """

        return prompt



    def _parse_ai_response_postman(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response to extract structured insights."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group(1))

            # If no JSON block found, try to parse the entire response as JSON
            import json
            return json.loads(response_text)

        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Response text: {response_text}...")
            # Return a structured fallback if parsing fails
            return {
                "command": response_text
            }
