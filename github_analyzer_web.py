#!/usr/bin/env python3
"""
GitHub Repository Analyzer Web Application

This module provides a web interface for the GitHub repository analyzer.
"""

import os
import json
import pickle
import uuid
from flask import Flask, request, render_template, jsonify, session, Response
from github_analyzer_api import GitHubAPIAnalyzer
from ai_analyzer import AIRepositoryAnalyzer

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create necessary directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data_store', exist_ok=True)

# Add custom template filter for generating color hashes
@app.template_filter('hash_code')
def hash_code_filter(s):
    """Convert a string to a numeric hash code."""
    return sum(ord(c) for c in str(s))

# Simple file-based storage for analysis results
def save_analysis_results(results):
    """Save analysis results to a file and return the ID."""
    result_id = str(uuid.uuid4())
    file_path = os.path.join('data_store', f"{result_id}.pkl")
    
    with open(file_path, 'wb') as f:
        pickle.dump(results, f)
    
    return result_id

def load_analysis_results(result_id):
    """Load analysis results from a file."""
    file_path = os.path.join('data_store', f"{result_id}.pkl")
    
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'rb') as f:
        return pickle.load(f)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a GitHub repository."""
    data = request.json
    repo_url = data.get('repo_url')
    github_token = data.get('github_token')
    gemini_api_key = data.get('gemini_api_key')
    generate_readme = data.get('generate_readme', False)
    force_generate_readme = data.get('force_generate_readme', False)
    use_ai = data.get('use_ai', False) and gemini_api_key
    
    if not repo_url:
        return jsonify({'error': 'Repository URL is required'}), 400
    
    try:
        # Create analyzer instance
        analyzer = GitHubAPIAnalyzer(repo_url, github_token)
        
        # Analyze repository
        results = analyzer.analyze()
        
        if not results:
            return jsonify({'error': 'Failed to analyze repository'}), 500
        
        # Use AI for enhanced analysis if requested and API key provided
        if use_ai:
            try:
                ai_analyzer = AIRepositoryAnalyzer(gemini_api_key)
                results = ai_analyzer.analyze_repository(results)
                results['ai_enabled'] = True
                
                # Generate README with AI if requested
                if (generate_readme and not results.get('readme_content')) or force_generate_readme:
                    generated_readme = ai_analyzer.generate_readme(results)
                    
                    # If forcing generation, store the original README separately
                    if force_generate_readme and results.get('readme_content'):
                        results['original_readme_content'] = results['readme_content']
                        
                    results['readme_content'] = generated_readme
                    results['readme_generated'] = True
                    results['ai_generated_readme'] = True
            except Exception as e:
                print(f"AI analysis failed: {e}")
                # Fall back to standard analysis
                results['ai_enabled'] = False
                results['ai_error'] = str(e)
        else:
            # Standard README generation if AI is not used
            if (generate_readme and not results.get('readme_content')) or force_generate_readme:
                generated_readme = analyzer.generate_readme(results)
                
                # If forcing generation, store the original README separately
                if force_generate_readme and results.get('readme_content'):
                    results['original_readme_content'] = results['readme_content']
                    
                results['readme_content'] = generated_readme
                results['readme_generated'] = True
                results['ai_generated_readme'] = False
        
        # Save results to file storage and store ID in session
        result_id = save_analysis_results(results)
        session['result_id'] = result_id
        
        return jsonify({'success': True, 'redirect': '/results'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API endpoint for analyzing a GitHub repository."""
    data = request.json
    repo_url = data.get('repo_url')
    github_token = data.get('github_token')
    gemini_api_key = data.get('gemini_api_key')
    generate_readme = data.get('generate_readme', False)
    force_generate_readme = data.get('force_generate_readme', False)
    use_ai = data.get('use_ai', False) and gemini_api_key
    
    if not repo_url:
        return jsonify({'error': 'Repository URL is required'}), 400
    
    try:
        # Create analyzer instance
        analyzer = GitHubAPIAnalyzer(repo_url, github_token)
        
        # Analyze repository
        results = analyzer.analyze()
        
        if not results:
            return jsonify({'error': 'Failed to analyze repository'}), 500
        
        # Use AI for enhanced analysis if requested and API key provided
        if use_ai:
            try:
                ai_analyzer = AIRepositoryAnalyzer(gemini_api_key)
                results = ai_analyzer.analyze_repository(results)
                results['ai_enabled'] = True
                
                # Generate README with AI if requested
                if (generate_readme and not results.get('readme_content')) or force_generate_readme:
                    generated_readme = ai_analyzer.generate_readme(results)
                    
                    # If forcing generation, store the original README separately
                    if force_generate_readme and results.get('readme_content'):
                        results['original_readme_content'] = results['readme_content']
                        
                    results['readme_content'] = generated_readme
                    results['readme_generated'] = True
                    results['ai_generated_readme'] = True
            except Exception as e:
                print(f"AI analysis failed: {e}")
                # Fall back to standard analysis
                results['ai_enabled'] = False
                results['ai_error'] = str(e)
        else:
            # Standard README generation if AI is not used
            if (generate_readme and not results.get('readme_content')) or force_generate_readme:
                generated_readme = analyzer.generate_readme(results)
                
                # If forcing generation, store the original README separately
                if force_generate_readme and results.get('readme_content'):
                    results['original_readme_content'] = results['readme_content']
                    
                results['readme_content'] = generated_readme
                results['readme_generated'] = True
                results['ai_generated_readme'] = False
        
        # Save results to file storage and return ID
        result_id = save_analysis_results(results)
        results['result_id'] = result_id
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    """Display analysis results."""
    if 'result_id' not in session:
        return "No analysis results found. Please analyze a repository first.", 404
    
    try:
        # Load results from file storage
        result_id = session['result_id']
        results = load_analysis_results(result_id)
        
        if not results:
            return "Analysis results not found. Please analyze the repository again.", 404
        
        return render_template('results.html', results=results)
    except Exception as e:
        return f"Error loading analysis results: {str(e)}", 500

def generate_documentation(results):
    """
    Generate documentation from analysis results.
    
    Args:
        results (dict): Analysis results
        
    Returns:
        str: Markdown documentation
    """
    repo_info = results.get('repo_info', {})
    language_stats = results.get('language_stats', {})
    readme_content = results.get('readme_content', '')
    repo_structure = results.get('repo_structure', {})
    functions = results.get('functions', [])
    classes = results.get('classes', [])
    features = results.get('features', [])
    
    # Generate markdown
    md = f"# {repo_info.get('name', 'Repository')} Documentation\n\n"
    
    # Repository information
    md += "## Repository Overview\n\n"
    md += f"**Name:** {repo_info.get('name', 'N/A')}\n\n"
    md += f"**Description:** {repo_info.get('description', 'No description available')}\n\n"
    md += f"**Stars:** {repo_info.get('stargazers_count', 'N/A')}\n\n"
    md += f"**Forks:** {repo_info.get('forks_count', 'N/A')}\n\n"
    md += f"**Last Updated:** {repo_info.get('updated_at', 'N/A')}\n\n"
    md += f"**License:** {repo_info.get('license', {}).get('name', 'Not specified')}\n\n"
    
    # Features
    md += "## Features and Technologies\n\n"
    if features:
        for feature in sorted(features):
            md += f"- {feature}\n"
    else:
        md += "No specific features detected.\n"
    
    # Repository structure
    md += "\n## Repository Structure\n\n"
    md += "```\n"
    
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
    
    md += print_structure(repo_structure)
    md += "```\n\n"
    
    # Language statistics
    md += "## Language Statistics\n\n"
    md += "| Language | Bytes |\n"
    md += "|----------|-------|\n"
    
    for lang, bytes_count in sorted(language_stats.items(), key=lambda x: x[1], reverse=True):
        md += f"| {lang} | {bytes_count} |\n"
    
    # Functions
    if functions:
        md += "\n## Key Functions\n\n"
        md += "| Function | File | Parameters | Language |\n"
        md += "|----------|------|------------|----------|\n"
        
        # Sort functions by file
        sorted_functions = sorted(functions, key=lambda x: (x.get('file', ''), x.get('name', '')))
        
        # Display up to 30 functions
        for func in sorted_functions[:30]:
            md += f"| `{func.get('name', '')}` | {func.get('file', '')} | `{func.get('params', '')}` | {func.get('language', '')} |\n"
        
        if len(sorted_functions) > 30:
            md += f"\n*... and {len(sorted_functions) - 30} more functions*\n"
    
    # Classes
    if classes:
        md += "\n## Key Classes\n\n"
        md += "| Class | File | Inheritance | Language |\n"
        md += "|-------|------|-------------|----------|\n"
        
        # Sort classes by file
        sorted_classes = sorted(classes, key=lambda x: (x.get('file', ''), x.get('name', '')))
        
        # Display up to 30 classes
        for cls in sorted_classes[:30]:
            md += f"| `{cls.get('name', '')}` | {cls.get('file', '')} | {cls.get('inheritance', '')} | {cls.get('language', '')} |\n"
        
        if len(sorted_classes) > 30:
            md += f"\n*... and {len(sorted_classes) - 30} more classes*\n"
    
    # Original README content
    if readme_content:
        md += "\n## Original README Content\n\n"
        md += readme_content
    
    return md

@app.route('/download')
def download():
    """Download documentation as markdown."""
    if 'result_id' not in session:
        return "No analysis results found. Please analyze a repository first.", 404
    
    try:
        # Load results from file storage
        result_id = session['result_id']
        results = load_analysis_results(result_id)
        
        if not results:
            return "Analysis results not found. Please analyze the repository again.", 404
        
        markdown_content = generate_documentation(results)
        
        repo_name = results.get('repo_info', {}).get('name', 'repository')
        
        return Response(
            markdown_content,
            mimetype='text/markdown',
            headers={'Content-Disposition': f'attachment;filename={repo_name}_documentation.md'}
        )
    except Exception as e:
        return f"Error generating documentation: {str(e)}", 500

@app.route('/download-readme')
def download_readme():
    """Download just the README file."""
    if 'result_id' not in session:
        return "No analysis results found. Please analyze a repository first.", 404
    
    try:
        # Load results from file storage
        result_id = session['result_id']
        results = load_analysis_results(result_id)
        
        if not results:
            return "Analysis results not found. Please analyze the repository again.", 404
        
        readme_content = results.get('readme_content', '')
        
        if not readme_content:
            return "No README content available.", 404
        
        repo_name = results.get('repo_info', {}).get('name', 'repository')
        
        return Response(
            readme_content,
            mimetype='text/markdown',
            headers={'Content-Disposition': f'attachment;filename={repo_name}_README.md'}
        )
    except Exception as e:
        return f"Error downloading README: {str(e)}", 500

@app.route('/download-original-readme')
def download_original_readme():
    """Download the original README file."""
    if 'result_id' not in session:
        return "No analysis results found. Please analyze a repository first.", 404
    
    try:
        # Load results from file storage
        result_id = session['result_id']
        results = load_analysis_results(result_id)
        
        if not results:
            return "Analysis results not found. Please analyze the repository again.", 404
        
        original_readme_content = results.get('original_readme_content', '')
        
        if not original_readme_content:
            return "No original README content available.", 404
        
        repo_name = results.get('repo_info', {}).get('name', 'repository')
        
        return Response(
            original_readme_content,
            mimetype='text/markdown',
            headers={'Content-Disposition': f'attachment;filename={repo_name}_original_README.md'}
        )
    except Exception as e:
        return f"Error downloading original README: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
