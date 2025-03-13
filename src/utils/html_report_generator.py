"""
HTML Report Generator for MATILDA Rule Discovery.

This module provides functionality to generate HTML reports for MATILDA's
discovered rules including TGDs and EGDs.
"""

import time
import json
import os
import logging
from typing import List, Dict, Any, Optional
from utils.rules import Rule, TGDRule, EGDRule


class HtmlReportGenerator:
    """Generates HTML reports for MATILDA rule discovery results."""
    
    def __init__(self, logger=None):
        """
        Initialize the HTML report generator.
        
        :param logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger("MATILDA.HtmlReportGenerator")
    
    def generate_report(self, 
                        output_path: str,
                        stats: Dict[str, Any], 
                        tgd_rules: List[Rule] = None, 
                        egd_rules: List[Rule] = None,
                        fd_rules: List[Rule] = None,
                        horn_rules: List[Rule] = None,
                        keys_rules: List[Rule] = None) -> bool:
        """
        Generate an HTML report with rules and statistics.
        
        :param output_path: Path to save the HTML report
        :param stats: Dictionary with discovery statistics
        :param tgd_rules: List of TGD rules to include
        :param egd_rules: List of EGD rules to include
        :param fd_rules: List of FD (Functional Dependency) rules to include
        :param horn_rules: List of HORN rules to include
        :param keys_rules: List of KEY rules to include
        :return: True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Prepare rule data
            tgd_rules_data = self._prepare_rule_data(tgd_rules or [])
            egd_rules_data = self._prepare_rule_data(egd_rules or [])
            fd_rules_data = self._prepare_rule_data(fd_rules or [])
            horn_rules_data = self._prepare_rule_data(horn_rules or [])
            keys_rules_data = self._prepare_rule_data(keys_rules or [])
            
            # Create HTML content
            html_content = self._create_html_content(stats, tgd_rules_data, egd_rules_data, 
                                                    fd_rules_data, horn_rules_data, keys_rules_data)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"HTML report generated successfully at {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return False
    
    def _prepare_rule_data(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """
        Convert rule objects to dictionary format for JSON serialization.
        
        :param rules: List of rule objects
        :return: List of rule dictionaries
        """
        result = []
        
        for rule in rules:
            rule_dict = {
                "display": getattr(rule, 'display', str(rule)),
                "support": getattr(rule, 'accuracy', 0),
                "confidence": getattr(rule, 'confidence', 0),
            }
            
            if isinstance(rule, TGDRule):
                rule_dict["type"] = "TGD"
                rule_dict["body"] = [str(pred) for pred in rule.body]
                rule_dict["head"] = [str(pred) for pred in rule.head]
            elif isinstance(rule, EGDRule):
                rule_dict["type"] = "EGD"
                rule_dict["body"] = [str(pred) for pred in rule.body]
                rule_dict["head"] = [list(eq) for eq in rule.head]
            
            result.append(rule_dict)
            
        return result
    
    def _create_html_content(self, stats: Dict[str, Any], 
                            tgd_rules_data: List[Dict[str, Any]], 
                            egd_rules_data: List[Dict[str, Any]],
                            fd_rules_data: List[Dict[str, Any]],
                            horn_rules_data: List[Dict[str, Any]],
                            keys_rules_data: List[Dict[str, Any]]) -> str:
        """
        Create the HTML content for the report.
        
        :param stats: Dictionary with statistics
        :param tgd_rules_data: List of prepared TGD rules data
        :param egd_rules_data: List of prepared EGD rules data
        :param fd_rules_data: List of prepared FD rules data
        :param horn_rules_data: List of prepared HORN rules data
        :param keys_rules_data: List of prepared KEY rules data
        :return: HTML string
        """
        # Serialize rule data as JSON to embed in JavaScript
        try:
            tgd_rules_js = json.dumps(tgd_rules_data)
            egd_rules_js = json.dumps(egd_rules_data)
            fd_rules_js = json.dumps(fd_rules_data)
            horn_rules_js = json.dumps(horn_rules_data)
            keys_rules_js = json.dumps(keys_rules_data)
        except Exception as e:
            self.logger.error(f"Error serializing rules for HTML report: {e}")
            tgd_rules_js = "[]"
            egd_rules_js = "[]"
            fd_rules_js = "[]"
            horn_rules_js = "[]"
            keys_rules_js = "[]"
        
        # HTML template
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>MATILDA Rule Discovery Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            color: #333;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ 
            color: #2c3e50; 
            margin-top: 20px;
        }}
        .stats-container {{ 
            display: flex; 
            flex-wrap: wrap; 
            margin: 20px 0;
        }}
        .stat-box {{ 
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin: 10px;
            min-width: 200px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex-grow: 1;
        }}
        .stat-title {{ 
            font-weight: bold; 
            color: #3498db;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 1.2em;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin-top: 20px;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 10px; 
            text-align: left; 
        }}
        th {{ 
            background-color: #f2f2f2; 
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{ 
            background-color: #f9f9f9; 
        }}
        tr:hover {{
            background-color: #f1f1f1;
        }}
        
        /* Tab styling */
        .tab {{
            overflow: hidden;
            border: 1px solid #ccc;
            background-color: #f1f1f1;
            border-radius: 5px 5px 0 0;
        }}
        .tab button {{
            background-color: inherit;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 16px;
            transition: 0.3s;
            font-size: 16px;
        }}
        .tab button:hover {{
            background-color: #ddd;
        }}
        .tab button.active {{
            background-color: #3498db;
            color: white;
        }}
        .tabcontent {{
            display: none;
            padding: 6px 12px;
            border: 1px solid #ccc;
            border-top: none;
            animation: fadeEffect 1s;
        }}
        @keyframes fadeEffect {{
            from {{opacity: 0;}}
            to {{opacity: 1;}}
        }}
        .rule-details {{
            background-color: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-left: 3px solid #3498db;
            border-radius: 0 5px 5px 0;
        }}
        pre {{
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: Consolas, monospace;
            font-size: 14px;
        }}
        .search-box {{
            margin: 15px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
        }}
        .search-input {{
            padding: 10px;
            margin-right: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            flex-grow: 1;
            min-width: 200px;
        }}
        .search-box select {{
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: white;
            min-width: 150px;
        }}
        .export-buttons {{
            margin: 20px 0;
            display: flex;
            flex-wrap: wrap;
        }}
        .export-buttons button {{
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            margin: 5px 10px 5px 0;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }}
        .export-buttons button:hover {{
            background-color: #45a049;
        }}
        .pagination {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        .pagination button {{
            background-color: #f1f1f1;
            color: black;
            padding: 8px 16px;
            margin: 0 4px;
            border: 1px solid #ddd;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.3s;
        }}
        .pagination button:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        .pagination button.active {{
            background-color: #3498db;
            color: white;
            border: 1px solid #3498db;
        }}
        .detail-button {{
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 10px;
            cursor: pointer;
        }}
        .detail-button:hover {{
            background-color: #2980b9;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        .modal-content {{
            background-color: white;
            margin: 10% auto;
            padding: 20px;
            border-radius: 5px;
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            position: relative;
        }}
        .close-button {{
            background-color: #f44336;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
        }}
        .close-button:hover {{
            background-color: #d32f2f;
        }}
        .summary-card {{
            background-color: #e8f4fb;
            border-left: 5px solid #3498db;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 5px 5px 0;
        }}
        @media print {{
            .tab, .search-box, .export-buttons, .pagination, .detail-button, .close-button {{
                display: none;
            }}
            .tabcontent {{
                display: block !important;
                border: none;
            }}
            table {{ page-break-inside: avoid; }}
            tr {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <h1>MATILDA Rule Discovery Report</h1>
    <p>Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <div class="summary-card">
        <h2>Summary</h2>
        <p>Total rules discovered: {stats.get("tgds_discovered", 0) + stats.get("egds_discovered", 0) + 
                                   stats.get("fds_discovered", 0) + stats.get("horns_discovered", 0) + 
                                   stats.get("keys_discovered", 0)}</p>
        <p>Total discovery time: {(stats.get("tgd_discovery_time", 0) + stats.get("egd_discovery_time", 0) + 
                                stats.get("fd_discovery_time", 0) + stats.get("horn_discovery_time", 0) + 
                                stats.get("keys_discovery_time", 0)):.2f} seconds</p>
    </div>
    
    <h2>Discovery Statistics</h2>
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-title">TGDs Discovered</div>
            <div class="stat-value">{stats.get("tgds_discovered", 0)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">EGDs Discovered</div>
            <div class="stat-value">{stats.get("egds_discovered", 0)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">FDs Discovered</div>
            <div class="stat-value">{stats.get("fds_discovered", 0)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">HORN Rules Discovered</div>
            <div class="stat-value">{stats.get("horns_discovered", 0)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">KEYs Discovered</div>
            <div class="stat-value">{stats.get("keys_discovered", 0)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">TGD Discovery Time</div>
            <div class="stat-value">{stats.get("tgd_discovery_time", 0):.2f} seconds</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">EGD Discovery Time</div>
            <div class="stat-value">{stats.get("egd_discovery_time", 0):.2f} seconds</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">FD Discovery Time</div>
            <div class="stat-value">{stats.get("fd_discovery_time", 0):.2f} seconds</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">HORN Discovery Time</div>
            <div class="stat-value">{stats.get("horn_discovery_time", 0):.2f} seconds</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">KEYs Discovery Time</div>
            <div class="stat-value">{stats.get("keys_discovery_time", 0):.2f} seconds</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. TGD Support</div>
            <div class="stat-value">{stats.get("tgd_avg_support", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. TGD Confidence</div>
            <div class="stat-value">{stats.get("tgd_avg_confidence", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. EGD Support</div>
            <div class="stat-value">{stats.get("egd_avg_support", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. EGD Confidence</div>
            <div class="stat-value">{stats.get("egd_avg_confidence", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. FD Support</div>
            <div class="stat-value">{stats.get("fd_avg_support", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. FD Confidence</div>
            <div class="stat-value">{stats.get("fd_avg_confidence", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. HORN Support</div>
            <div class="stat-value">{stats.get("horn_avg_support", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. HORN Confidence</div>
            <div class="stat-value">{stats.get("horn_avg_confidence", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. KEY Support</div>
            <div class="stat-value">{stats.get("keys_avg_support", 0):.4f}</div>
        </div>
        <div class="stat-box">
            <div class="stat-title">Avg. KEY Confidence</div>
            <div class="stat-value">{stats.get("keys_avg_confidence", 0):.4f}</div>
        </div>
    </div>
    
    <div class="export-buttons">
        <button onclick="exportRulesToCSV()">Export to CSV</button>
        <button onclick="exportRulesToJSON()">Export to JSON</button>
        <button onclick="window.print()">Print Report</button>
    </div>
    
    <h2>Rule Results</h2>
    <div class="tab">
        <button class="tablinks active" onclick="openRuleTab(event, 'TGDRules')">TGD Rules</button>
        <button class="tablinks" onclick="openRuleTab(event, 'EGDRules')">EGD Rules</button>
        <button class="tablinks" onclick="openRuleTab(event, 'FDRules')">FD Rules</button>
        <button class="tablinks" onclick="openRuleTab(event, 'HORNRules')">HORN Rules</button>
        <button class="tablinks" onclick="openRuleTab(event, 'KEYSRules')">KEY Rules</button>
    </div>

    <div id="TGDRules" class="tabcontent" style="display: block;">
        <h3>Tuple-Generating Dependencies (TGDs)</h3>
        <p>Total TGDs discovered: {stats.get("tgds_discovered", 0)}</p>
        
        <div class="search-box">
            <input type="text" id="tgdSearchInput" class="search-input" placeholder="Search TGD rules..." onkeyup="searchRules('TGD')">
            <select id="tgdSortSelect" onchange="sortRules('TGD')">
                <option value="default">Sort by default</option>
                <option value="support-desc">Sort by support (high to low)</option>
                <option value="confidence-desc">Sort by confidence (high to low)</option>
                <option value="complexity-asc">Sort by complexity (simple to complex)</option>
            </select>
        </div>
        
        <div id="tgdPagination" class="pagination"></div>
        
        <table id="tgdTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rule</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">Loading TGD rules...</td>
                </tr>
            </tbody>
        </table>
        
        <div id="tgdPaginationBottom" class="pagination"></div>
    </div>

    <div id="EGDRules" class="tabcontent">
        <h3>Equality-Generating Dependencies (EGDs)</h3>
        <p>Total EGDs discovered: {stats.get("egds_discovered", 0)}</p>
        
        <div class="search-box">
            <input type="text" id="egdSearchInput" class="search-input" placeholder="Search EGD rules..." onkeyup="searchRules('EGD')">
            <select id="egdSortSelect" onchange="sortRules('EGD')">
                <option value="default">Sort by default</option>
                <option value="support-desc">Sort by support (high to low)</option>
                <option value="confidence-desc">Sort by confidence (high to low)</option>
                <option value="complexity-asc">Sort by complexity (simple to complex)</option>
            </select>
        </div>
        
        <div id="egdPagination" class="pagination"></div>
        
        <table id="egdTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rule</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">Loading EGD rules...</td>
                </tr>
            </tbody>
        </table>
        
        <div id="egdPaginationBottom" class="pagination"></div>
    </div>
    
    <div id="FDRules" class="tabcontent">
        <h3>Functional Dependencies (FDs)</h3>
        <p>Total FDs discovered: {stats.get("fds_discovered", 0)}</p>
        
        <div class="search-box">
            <input type="text" id="fdSearchInput" class="search-input" placeholder="Search FD rules..." onkeyup="searchRules('FD')">
            <select id="fdSortSelect" onchange="sortRules('FD')">
                <option value="default">Sort by default</option>
                <option value="support-desc">Sort by support (high to low)</option>
                <option value="confidence-desc">Sort by confidence (high to low)</option>
                <option value="complexity-asc">Sort by complexity (simple to complex)</option>
            </select>
        </div>
        
        <div id="fdPagination" class="pagination"></div>
        
        <table id="fdTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rule</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">Loading FD rules...</td>
                </tr>
            </tbody>
        </table>
        
        <div id="fdPaginationBottom" class="pagination"></div>
    </div>
    
    <div id="HORNRules" class="tabcontent">
        <h3>Horn Rules</h3>
        <p>Total HORN rules discovered: {stats.get("horns_discovered", 0)}</p>
        
        <div class="search-box">
            <input type="text" id="hornSearchInput" class="search-input" placeholder="Search HORN rules..." onkeyup="searchRules('HORN')">
            <select id="hornSortSelect" onchange="sortRules('HORN')">
                <option value="default">Sort by default</option>
                <option value="support-desc">Sort by support (high to low)</option>
                <option value="confidence-desc">Sort by confidence (high to low)</option>
                <option value="complexity-asc">Sort by complexity (simple to complex)</option>
            </select>
        </div>
        
        <div id="hornPagination" class="pagination"></div>
        
        <table id="hornTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rule</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">Loading HORN rules...</td>
                </tr>
            </tbody>
        </table>
        
        <div id="hornPaginationBottom" class="pagination"></div>
    </div>
    
    <div id="KEYSRules" class="tabcontent">
        <h3>Key Rules</h3>
        <p>Total KEY rules discovered: {stats.get("keys_discovered", 0)}</p>
        
        <div class="search-box">
            <input type="text" id="keysSearchInput" class="search-input" placeholder="Search KEY rules..." onkeyup="searchRules('KEYS')">
            <select id="keysSortSelect" onchange="sortRules('KEYS')">
                <option value="default">Sort by default</option>
                <option value="support-desc">Sort by support (high to low)</option>
                <option value="confidence-desc">Sort by confidence (high to low)</option>
                <option value="complexity-asc">Sort by complexity (simple to complex)</option>
            </select>
        </div>
        
        <div id="keysPagination" class="pagination"></div>
        
        <table id="keysTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rule</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">Loading KEY rules...</td>
                </tr>
            </tbody>
        </table>
        
        <div id="keysPaginationBottom" class="pagination"></div>
    </div>

    <!-- Modal for rule details -->
    <div id="ruleDetailModal" class="modal">
        <div class="modal-content">
            <div id="ruleDetailContent"></div>
            <button class="close-button" onclick="closeModal()">Close</button>
        </div>
    </div>

    <script>
    // Rule data
    const tgdRules = {tgd_rules_js};
    const egdRules = {egd_rules_js};
    const fdRules = {fd_rules_js};
    const hornRules = {horn_rules_js};
    const keysRules = {keys_rules_js};
    
    // Pagination variables
    const rulesPerPage = 25;
    let currentTGDPage = 1;
    let currentEGDPage = 1;
    let currentFDPage = 1;
    let currentHORNPage = 1;
    let currentKEYSPage = 1;
    let filteredTGDRules = [...tgdRules];
    let filteredEGDRules = [...egdRules];
    let filteredFDRules = [...fdRules];
    let filteredHORNRules = [...hornRules];
    let filteredKEYSRules = [...keysRules];
    
    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {{
        displayTGDRules();
        displayEGDRules();
        displayFDRules();
        displayHORNRules();
        displayKEYSRules();
    }});
    
    function openRuleTab(evt, tabName) {{
        const tabcontent = document.getElementsByClassName("tabcontent");
        for (let i = 0; i < tabcontent.length; i++) {{
            tabcontent[i].style.display = "none";
        }}
        
        const tablinks = document.getElementsByClassName("tablinks");
        for (let i = 0; i < tablinks.length; i++) {{
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }}
        
        document.getElementById(tabName).style.display = "block";
        evt.currentTarget.className += " active";
    }}
    
    function displayTGDRules() {{
        updatePagination('TGD');
        
        const tgdTable = document.getElementById('tgdTable').getElementsByTagName('tbody')[0];
        tgdTable.innerHTML = '';
        
        const startIndex = (currentTGDPage - 1) * rulesPerPage;
        const endIndex = startIndex + rulesPerPage;
        const pageTGDRules = filteredTGDRules.slice(startIndex, endIndex);
        
        if (pageTGDRules.length > 0) {{
            pageTGDRules.forEach((rule, idx) => {{
                const row = tgdTable.insertRow();
                row.insertCell(0).textContent = startIndex + idx + 1;
                row.insertCell(1).textContent = rule.display || 'No display available';
                row.insertCell(2).textContent = (rule.support || 0).toFixed(4);
                row.insertCell(3).textContent = (rule.confidence || 0).toFixed(4);
                
                const detailsCell = row.insertCell(4);
                const detailsButton = document.createElement('button');
                detailsButton.textContent = 'Show Details';
                detailsButton.className = 'detail-button';
                detailsButton.onclick = function() {{ showRuleDetails(rule, 'TGD'); }};
                detailsCell.appendChild(detailsButton);
            }});
        }} else {{
            const row = tgdTable.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 5;
            cell.textContent = 'No TGD rules available or matching the search criteria';
        }}
    }}
    
    function displayEGDRules() {{
        updatePagination('EGD');
        
        const egdTable = document.getElementById('egdTable').getElementsByTagName('tbody')[0];
        egdTable.innerHTML = '';
        
        const startIndex = (currentEGDPage - 1) * rulesPerPage;
        const endIndex = startIndex + rulesPerPage;
        const pageEGDRules = filteredEGDRules.slice(startIndex, endIndex);
        
        if (pageEGDRules.length > 0) {{
            pageEGDRules.forEach((rule, idx) => {{
                const row = egdTable.insertRow();
                row.insertCell(0).textContent = startIndex + idx + 1;
                row.insertCell(1).textContent = rule.display || 'No display available';
                row.insertCell(2).textContent = (rule.support || 0).toFixed(4);
                row.insertCell(3).textContent = (rule.confidence || 0).toFixed(4);
                
                const detailsCell = row.insertCell(4);
                const detailsButton = document.createElement('button');
                detailsButton.textContent = 'Show Details';
                detailsButton.className = 'detail-button';
                detailsButton.onclick = function() {{ showRuleDetails(rule, 'EGD'); }};
                detailsCell.appendChild(detailsButton);
            }});
        }} else {{
            const row = egdTable.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 5;
            cell.textContent = 'No EGD rules available or matching the search criteria';
        }}
    }}
    
    function displayFDRules() {{
        updatePagination('FD');
        
        const fdTable = document.getElementById('fdTable').getElementsByTagName('tbody')[0];
        fdTable.innerHTML = '';
        
        const startIndex = (currentFDPage - 1) * rulesPerPage;
        const endIndex = startIndex + rulesPerPage;
        const pageFDRules = filteredFDRules.slice(startIndex, endIndex);
        
        if (pageFDRules.length > 0) {{
            pageFDRules.forEach((rule, idx) => {{
                const row = fdTable.insertRow();
                row.insertCell(0).textContent = startIndex + idx + 1;
                row.insertCell(1).textContent = rule.display || 'No display available';
                row.insertCell(2).textContent = (rule.support || 0).toFixed(4);
                row.insertCell(3).textContent = (rule.confidence || 0).toFixed(4);
                
                const detailsCell = row.insertCell(4);
                const detailsButton = document.createElement('button');
                detailsButton.textContent = 'Show Details';
                detailsButton.className = 'detail-button';
                detailsButton.onclick = function() {{ showRuleDetails(rule, 'FD'); }};
                detailsCell.appendChild(detailsButton);
            }});
        }} else {{
            const row = fdTable.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 5;
            cell.textContent = 'No FD rules available or matching the search criteria';
        }}
    }}
    
    function displayHORNRules() {{
        updatePagination('HORN');
        
        const hornTable = document.getElementById('hornTable').getElementsByTagName('tbody')[0];
        hornTable.innerHTML = '';
        
        const startIndex = (currentHORNPage - 1) * rulesPerPage;
        const endIndex = startIndex + rulesPerPage;
        const pageHORNRules = filteredHORNRules.slice(startIndex, endIndex);
        
        if (pageHORNRules.length > 0) {{
            pageHORNRules.forEach((rule, idx) => {{
                const row = hornTable.insertRow();
                row.insertCell(0).textContent = startIndex + idx + 1;
                row.insertCell(1).textContent = rule.display || 'No display available';
                row.insertCell(2).textContent = (rule.support || 0).toFixed(4);
                row.insertCell(3).textContent = (rule.confidence || 0).toFixed(4);
                
                const detailsCell = row.insertCell(4);
                const detailsButton = document.createElement('button');
                detailsButton.textContent = 'Show Details';
                detailsButton.className = 'detail-button';
                detailsButton.onclick = function() {{ showRuleDetails(rule, 'HORN'); }};
                detailsCell.appendChild(detailsButton);
            }});
        }} else {{
            const row = hornTable.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 5;
            cell.textContent = 'No HORN rules available or matching the search criteria';
        }}
    }}
    
    function displayKEYSRules() {{
        updatePagination('KEYS');
        
        const keysTable = document.getElementById('keysTable').getElementsByTagName('tbody')[0];
        keysTable.innerHTML = '';
        
        const startIndex = (currentKEYSPage - 1) * rulesPerPage;
        const endIndex = startIndex + rulesPerPage;
        const pageKEYSRules = filteredKEYSRules.slice(startIndex, endIndex);
        
        if (pageKEYSRules.length > 0) {{
            pageKEYSRules.forEach((rule, idx) => {{
                const row = keysTable.insertRow();
                row.insertCell(0).textContent = startIndex + idx + 1;
                row.insertCell(1).textContent = rule.display || 'No display available';
                row.insertCell(2).textContent = (rule.support || 0).toFixed(4);
                row.insertCell(3).textContent = (rule.confidence || 0).toFixed(4);
                
                const detailsCell = row.insertCell(4);
                const detailsButton = document.createElement('button');
                detailsButton.textContent = 'Show Details';
                detailsButton.className = 'detail-button';
                detailsButton.onclick = function() {{ showRuleDetails(rule, 'KEYS'); }};
                detailsCell.appendChild(detailsButton);
            }});
        }} else {{
            const row = keysTable.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 5;
            cell.textContent = 'No KEY rules available or matching the search criteria';
        }}
    }}
    
    function updatePagination(ruleType) {{
        const paginationContainer = document.getElementById(`${{ruleType.toLowerCase()}}Pagination`);
        const paginationContainerBottom = document.getElementById(`${{ruleType.toLowerCase()}}PaginationBottom`);
        
        let rulesArray;
        let currentPage;
        
        switch(ruleType) {{
            case 'TGD':
                rulesArray = filteredTGDRules;
                currentPage = currentTGDPage;
                break;
            case 'EGD':
                rulesArray = filteredEGDRules;
                currentPage = currentEGDPage;
                break;
            case 'FD':
                rulesArray = filteredFDRules;
                currentPage = currentFDPage;
                break;
            case 'HORN':
                rulesArray = filteredHORNRules;
                currentPage = currentHORNPage;
                break;
            case 'KEYS':
                rulesArray = filteredKEYSRules;
                currentPage = currentKEYSPage;
                break;
        }}
        
        const totalPages = Math.ceil(rulesArray.length / rulesPerPage);
        
        let paginationHtml = '';
        
        // Previous button
        paginationHtml += `<button ${{currentPage === 1 ? 'disabled' : ''}} onclick="changePage(${{currentPage - 1}}, '${{ruleType}}')">&laquo; Previous</button>`;
        
        // Page numbers
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        if (startPage > 1) {{
            paginationHtml += `<button onclick="changePage(1, '${{ruleType}}')">1</button>`;
            if (startPage > 2) {{
                paginationHtml += `<span>...</span>`;
            }}
        }}
        
        for (let i = startPage; i <= endPage; i++) {{
            paginationHtml += `<button ${{i === currentPage ? 'class="active"' : ''}} onclick="changePage(${{i}}, '${{ruleType}}')">${{i}}</button>`;
        }}
        
        if (endPage < totalPages) {{
            if (endPage < totalPages - 1) {{
                paginationHtml += `<span>...</span>`;
            }}
            paginationHtml += `<button onclick="changePage(${{totalPages}}, '${{ruleType}}')">${{totalPages}}</button>`;
        }}
        
        // Next button
        paginationHtml += `<button ${{currentPage === totalPages || totalPages === 0 ? 'disabled' : ''}} onclick="changePage(${{currentPage + 1}}, '${{ruleType}}')">Next &raquo;</button>`;
        
        paginationContainer.innerHTML = paginationHtml;
        paginationContainerBottom.innerHTML = paginationHtml;
    }}
    
    function changePage(pageNumber, ruleType) {{
        switch(ruleType) {{
            case 'TGD':
                currentTGDPage = pageNumber;
                displayTGDRules();
                break;
            case 'EGD':
                currentEGDPage = pageNumber;
                displayEGDRules();
                break;
            case 'FD':
                currentFDPage = pageNumber;
                displayFDRules();
                break;
            case 'HORN':
                currentHORNPage = pageNumber;
                displayHORNRules();
                break;
            case 'KEYS':
                currentKEYSPage = pageNumber;
                displayKEYSRules();
                break;
        }}
    }}
    
    function searchRules(ruleType) {{
        const searchInput = document.getElementById(`${{ruleType.toLowerCase()}}SearchInput`).value.toLowerCase();
        
        switch(ruleType) {{
            case 'TGD':
                filteredTGDRules = tgdRules.filter(rule => {{
                    return (rule.display && rule.display.toLowerCase().includes(searchInput)) || 
                    (rule.body && rule.body.some(p => p.toLowerCase().includes(searchInput))) || 
                    (rule.head && rule.head.some(p => p.toLowerCase().includes(searchInput)));
                }});
                currentTGDPage = 1;
                displayTGDRules();
                break;
            case 'EGD':
                filteredEGDRules = egdRules.filter(rule => {{
                    return (rule.display && rule.display.toLowerCase().includes(searchInput)) || 
                    (rule.body && rule.body.some(p => p.toLowerCase().includes(searchInput))) || 
                    (rule.head && rule.head.some(eq => eq.some(v => v.toLowerCase().includes(searchInput))));
                }});
                currentEGDPage = 1;
                displayEGDRules();
                break;
            case 'FD':
                filteredFDRules = fdRules.filter(rule => {{
                    return (rule.display && rule.display.toLowerCase().includes(searchInput)) || 
                    (rule.body && rule.body.some(p => p.toLowerCase().includes(searchInput))) || 
                    (rule.head && rule.head.some(p => p.toLowerCase().includes(searchInput)));
                }});
                currentFDPage = 1;
                displayFDRules();
                break;
            case 'HORN':
                filteredHORNRules = hornRules.filter(rule => {{
                    return (rule.display && rule.display.toLowerCase().includes(searchInput)) || 
                    (rule.body && rule.body.some(p => p.toLowerCase().includes(searchInput))) || 
                    (rule.head && rule.head.some(p => p.toLowerCase().includes(searchInput)));
                }});
                currentHORNPage = 1;
                displayHORNRules();
                break;
            case 'KEYS':
                filteredKEYSRules = keysRules.filter(rule => {{
                    return (rule.display && rule.display.toLowerCase().includes(searchInput)) || 
                    (rule.body && rule.body.some(p => p.toLowerCase().includes(searchInput))) || 
                    (rule.head && rule.head.some(p => p.toLowerCase().includes(searchInput)));
                }});
                currentKEYSPage = 1;
                displayKEYSRules();
                break;
        }}
    }}
    
    function sortRules(ruleType) {{
        const sortSelect = document.getElementById(`${{ruleType.toLowerCase()}}SortSelect`);
        const sortOption = sortSelect.value;
        
        const sortFunctions = {{
            'default': (a, b) => 0, // Keep original order
            'support-desc': (a, b) => (b.support || 0) - (a.support || 0),
            'confidence-desc': (a, b) => (b.confidence || 0) - (a.confidence || 0),
            'complexity-asc': (a, b) => {{
                // Sort by complexity (e.g., number of predicates in body + head)
                const complexityA = (a.body ? a.body.length : 0) + (a.head ? a.head.length : 0);
                const complexityB = (b.body ? b.body.length : 0) + (b.head ? b.head.length : 0);
                return complexityA - complexityB;
            }}
        }};
        
        switch(ruleType) {{
            case 'TGD':
                filteredTGDRules.sort(sortFunctions[sortOption]);
                currentTGDPage = 1;
                displayTGDRules();
                break;
            case 'EGD':
                filteredEGDRules.sort(sortFunctions[sortOption]);
                currentEGDPage = 1;
                displayEGDRules();
                break;
            case 'FD':
                filteredFDRules.sort(sortFunctions[sortOption]);
                currentFDPage = 1;
                displayFDRules();
                break;
            case 'HORN':
                filteredHORNRules.sort(sortFunctions[sortOption]);
                currentHORNPage = 1;
                displayHORNRules();
                break;
            case 'KEYS':
                filteredKEYSRules.sort(sortFunctions[sortOption]);
                currentKEYSPage = 1;
                displayKEYSRules();
                break;
        }}
    }}
    
    function showRuleDetails(rule, ruleType) {{
        let detailsHtml = `<div class="rule-details">`;
        
        detailsHtml += `<h3>${{rule.display || 'Rule details'}}</h3>`;
        detailsHtml += `<p><strong>Type:</strong> ${{ruleType}}</p>`;
        detailsHtml += `<p><strong>Support:</strong> ${{(rule.support || 0).toFixed(4)}}</p>`;
        detailsHtml += `<p><strong>Confidence:</strong> ${{(rule.confidence || 0).toFixed(4)}}</p>`;
        
        switch(ruleType) {{
            case 'TGD':
            case 'FD':
            case 'HORN':
            case 'KEYS':
                detailsHtml += `<p><strong>Body:</strong></p><pre>${{(rule.body ? rule.body.join('\\n') : 'No body predicates')}}</pre>`;
                detailsHtml += `<p><strong>Head:</strong></p><pre>${{(rule.head ? rule.head.join('\\n') : 'No head predicates')}}</pre>`;
                break;
            case 'EGD':
                detailsHtml += `<p><strong>Body:</strong></p><pre>${{(rule.body ? rule.body.join('\\n') : 'No body predicates')}}</pre>`;
                detailsHtml += `<p><strong>Equality:</strong></p><pre>${{(rule.head ? rule.head.map(eq => eq.join(' = ')).join('\\n') : 'No equality predicates')}}</pre>`;
                break;
        }}
        
        detailsHtml += `</div>`;
        
        // Display in modal
        document.getElementById('ruleDetailContent').innerHTML = detailsHtml;
        document.getElementById('ruleDetailModal').style.display = 'block';
    }}
    
    function closeModal() {{
        document.getElementById('ruleDetailModal').style.display = 'none';
    }}
    
    function exportRulesToCSV() {{
        // Préparer les données CSV
        let csvContent = 'data:text/csv;charset=utf-8,';
        csvContent += 'Type,Rule,Support,Confidence\\n';
        
        // Ajouter les règles TGD
        tgdRules.forEach(rule => {{
            csvContent += `TGD,"${{rule.display.replace(/"/g, '""')}}",${{(rule.support || 0).toFixed(4)}},${{(rule.confidence || 0).toFixed(4)}}\\n`;
        }});
        
        // Ajouter les règles EGD
        egdRules.forEach(rule => {{
            csvContent += `EGD,"${{rule.display.replace(/"/g, '""')}}",${{(rule.support || 0).toFixed(4)}},${{(rule.confidence || 0).toFixed(4)}}\\n`;
        }});
        
        // Ajouter les règles FD
        fdRules.forEach(rule => {{
            csvContent += `FD,"${{rule.display.replace(/"/g, '""')}}",${{(rule.support || 0).toFixed(4)}},${{(rule.confidence || 0).toFixed(4)}}\\n`;
        }});
        
        // Ajouter les règles HORN
        hornRules.forEach(rule => {{
            csvContent += `HORN,"${{rule.display.replace(/"/g, '""')}}",${{(rule.support || 0).toFixed(4)}},${{(rule.confidence || 0).toFixed(4)}}\\n`;
        }});
        
        // Ajouter les règles KEYS
        keysRules.forEach(rule => {{
            csvContent += `KEYS,"${{rule.display.replace(/"/g, '""')}}",${{(rule.support || 0).toFixed(4)}},${{(rule.confidence || 0).toFixed(4)}}\\n`;
        }});
        
        // Créer un lien de téléchargement
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', 'matilda_rules_' + new Date().toISOString().slice(0, 10) + '.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }}
    
    function exportRulesToJSON() {{
        // Préparer les données JSON
        const jsonData = {{
            tgd_rules: tgdRules,
            egd_rules: egdRules,
            fd_rules: fdRules,
            horn_rules: hornRules,
            keys_rules: keysRules,
            stats: {{
                tgd_count: tgdRules.length,
                egd_count: egdRules.length,
                fd_count: fdRules.length,
                horn_count: hornRules.length,
                keys_count: keysRules.length,
                export_date: new Date().toISOString()
            }}
        }};
        
        // Créer un lien de téléchargement
        const jsonString = JSON.stringify(jsonData, null, 2);
        const blob = new Blob([jsonString], {{type: 'application/json'}});
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', 'matilda_rules_' + new Date().toISOString().slice(0, 10) + '.json');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }}
    </script>
</body>
</html>
"""
        
        return html_content

# Méthodes d'exportation supplémentaires pour différents formats

def export_rules_to_csv(tgd_rules: List[Rule], egd_rules: List[Rule], output_path: str) -> bool:
    """
    Export rules to CSV format.
    
    :param tgd_rules: List of TGD rules
    :param egd_rules: List of EGD rules
    :param output_path: Output file path
    :return: True if successful, False otherwise
    """
    try:
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["Type", "Rule", "Support", "Confidence"])
            
            # Write TGD rules
            for rule in tgd_rules:
                support = getattr(rule, 'accuracy', 0)
                confidence = getattr(rule, 'confidence', 0)
                writer.writerow(["TGD", rule.display, f"{support:.4f}", f"{confidence:.4f}"])
            
            # Write EGD rules
            for rule in egd_rules:
                support = getattr(rule, 'accuracy', 0)
                confidence = getattr(rule, 'confidence', 0)
                writer.writerow(["EGD", rule.display, f"{support:.4f}", f"{confidence:.4f}"])
                
        return True
        
    except Exception as e:
        logging.error(f"Error exporting rules to CSV: {e}")
        return False

def export_rules_to_json(
    tgd_rules: List[Rule], 
    egd_rules: List[Rule], 
    output_path: str, 
    include_stats: bool = True, 
    fd_rules: List[Rule] = None, 
    horn_rules: List[Rule] = None, 
    keys_rules: List[Rule] = None
) -> bool:
    """
    Export rules to JSON format.
    
    :param tgd_rules: List of TGD rules
    :param egd_rules: List of EGD rules
    :param output_path: Output file path
    :param include_stats: Whether to include statistics in the output
    :param fd_rules: List of FD (Functional Dependency) rules
    :param horn_rules: List of HORN rules
    :param keys_rules: List of KEY rules
    :return: True if successful, False otherwise
    """
    try:
        # Initialize an instance without a logger to use its methods
        report_gen = HtmlReportGenerator()
        
        tgd_data = report_gen._prepare_rule_data(tgd_rules)
        egd_data = report_gen._prepare_rule_data(egd_rules)
        fd_data = report_gen._prepare_rule_data(fd_rules or [])
        horn_data = report_gen._prepare_rule_data(horn_rules or [])
        keys_data = report_gen._prepare_rule_data(keys_rules or [])
        
        data = {
            "tgd_rules": tgd_data,
            "egd_rules": egd_data,
            "fd_rules": fd_data,
            "horn_rules": horn_data,
            "keys_rules": keys_data
        }
        
        if include_stats:
            data["stats"] = {
                "tgd_count": len(tgd_rules),
                "egd_count": len(egd_rules),
                "fd_count": len(fd_rules or []),
                "horn_count": len(horn_rules or []),
                "keys_count": len(keys_rules or []),
                "export_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tgd_avg_support": sum(getattr(rule, 'accuracy', 0) for rule in tgd_rules) / len(tgd_rules) if tgd_rules else 0,
                "tgd_avg_confidence": sum(getattr(rule, 'confidence', 0) for rule in tgd_rules) / len(tgd_rules) if tgd_rules else 0,
                "egd_avg_support": sum(getattr(rule, 'accuracy', 0) for rule in egd_rules) / len(egd_rules) if egd_rules else 0,
                "egd_avg_confidence": sum(getattr(rule, 'confidence', 0) for rule in egd_rules) / len(egd_rules) if egd_rules else 0,
                "fd_avg_support": sum(getattr(rule, 'accuracy', 0) for rule in (fd_rules or [])) / len(fd_rules) if fd_rules else 0,
                "fd_avg_confidence": sum(getattr(rule, 'confidence', 0) for rule in (fd_rules or [])) / len(fd_rules) if fd_rules else 0,
                "horn_avg_support": sum(getattr(rule, 'accuracy', 0) for rule in (horn_rules or [])) / len(horn_rules) if horn_rules else 0,
                "horn_avg_confidence": sum(getattr(rule, 'confidence', 0) for rule in (horn_rules or [])) / len(horn_rules) if horn_rules else 0,
                "keys_avg_support": sum(getattr(rule, 'accuracy', 0) for rule in (keys_rules or [])) / len(keys_rules) if keys_rules else 0,
                "keys_avg_confidence": sum(getattr(rule, 'confidence', 0) for rule in (keys_rules or [])) / len(keys_rules) if keys_rules else 0
            }
            
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        return True
            
    except Exception as e:
        logging.error(f"Error exporting rules to JSON: {e}")
        return False