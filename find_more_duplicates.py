#!/usr/bin/env python3
"""
Find more semantic duplicates beyond exact matches
"""

import os
import ast
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class SemanticDuplicateFinder:
    def __init__(self):
        self.patterns = defaultdict(list)
        
    def analyze_file(self, filepath: str):
        """Analyze Python file for common patterns"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Pattern 1: Logger initialization
            logger_pattern = r'(logger|self\.logger)\s*=\s*(logging\.getLogger|getLogger)\('
            if re.search(logger_pattern, content):
                self.patterns['logger_init'].append(filepath)
                
            # Pattern 2: File path construction  
            path_pattern = r'os\.path\.(join|dirname|abspath)\([^)]+\)'
            matches = re.findall(path_pattern, content)
            if len(matches) > 3:
                self.patterns['path_construction'].append((filepath, len(matches)))
                
            # Pattern 3: JSON loading/saving
            json_pattern = r'(json\.dump|json\.load|json\.dumps|json\.loads)\s*\('
            if re.search(json_pattern, content):
                self.patterns['json_operations'].append(filepath)
                
            # Pattern 4: Error handling patterns
            try_except_pattern = r'try:\s*\n.*?\nexcept.*?:\s*\n.*?(raise|pass|continue)'
            if re.search(try_except_pattern, content, re.DOTALL):
                self.patterns['error_handling'].append(filepath)
                
            # Pattern 5: Config/settings loading
            config_pattern = r'(config|settings|params)\s*=\s*(\{|dict\(|.*\.get\()'
            if re.search(config_pattern, content):
                self.patterns['config_loading'].append(filepath)
                
            # Pattern 6: Timestamp generation
            timestamp_pattern = r'datetime\.now\(\)\.(isoformat|strftime)\('
            if re.search(timestamp_pattern, content):
                self.patterns['timestamp_generation'].append(filepath)
                
            # Pattern 7: Data validation
            validation_pattern = r'if\s+not\s+\w+.*?:\s*\n\s*(raise|return)'
            matches = re.findall(validation_pattern, content)
            if len(matches) > 2:
                self.patterns['data_validation'].append((filepath, len(matches)))
                
        except Exception as e:
            pass
            
    def analyze_directory(self, directory: str):
        """Analyze all Python files in directory"""
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    self.analyze_file(filepath)
                    
    def find_refactoring_opportunities(self):
        """Identify patterns that could be refactored"""
        opportunities = []
        
        for pattern, files in self.patterns.items():
            if len(files) > 3:  # Pattern appears in more than 3 files
                if pattern == 'path_construction':
                    # Files with many path operations
                    heavy_users = [f for f, count in files if count > 5]
                    if heavy_users:
                        opportunities.append({
                            'pattern': 'Path construction',
                            'description': 'Multiple files construct paths repeatedly',
                            'files': heavy_users[:5],
                            'suggestion': 'Create PathUtils module with common path helpers'
                        })
                        
                elif pattern == 'logger_init':
                    opportunities.append({
                        'pattern': 'Logger initialization',
                        'description': f'{len(files)} files initialize loggers',
                        'files': files[:5],
                        'suggestion': 'Create LoggerMixin or get_logger() utility'
                    })
                    
                elif pattern == 'timestamp_generation':
                    opportunities.append({
                        'pattern': 'Timestamp generation',
                        'description': f'{len(files)} files generate ISO timestamps',
                        'files': files[:5],
                        'suggestion': 'Create timestamp utilities module'
                    })
                    
                elif pattern == 'data_validation':
                    heavy_validators = [f for f, count in files if count > 4]
                    if heavy_validators:
                        opportunities.append({
                            'pattern': 'Data validation',
                            'description': 'Multiple validation patterns repeated',
                            'files': heavy_validators[:5],
                            'suggestion': 'Create validation decorators or utilities'
                        })
                        
        return opportunities

def main():
    finder = SemanticDuplicateFinder()
    
    print("🔍 Analyzing for semantic patterns...")
    finder.analyze_directory('./tasks')
    
    opportunities = finder.find_refactoring_opportunities()
    
    print("\n📊 REFACTORING OPPORTUNITIES:")
    print("=" * 80)
    
    for opp in opportunities:
        print(f"\n🎯 {opp['pattern']}")
        print(f"   {opp['description']}")
        print(f"   Suggestion: {opp['suggestion']}")
        print("   Example files:")
        for f in opp['files']:
            print(f"   - {os.path.relpath(f, '.')}")
            
    print(f"\n📈 Total patterns analyzed: {len(finder.patterns)}")
    print(f"⚡ Refactoring opportunities: {len(opportunities)}")

if __name__ == '__main__':
    main()