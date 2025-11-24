from flask import Flask, render_template, request, jsonify
import os
from scraper import WebsiteScraper
import threading
import time
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# Enhanced parsing functions to extract detailed data from analysis text
def get_company_name(url):
    """Extract company name from URL"""
    try:
        # Remove protocol and www
        clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
        # Get domain name
        domain = clean_url.split('/')[0]
        # Remove .com, .org, etc.
        name = domain.split('.')[0]
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in name.split('-'))
    except:
        return "Unknown"

def extract_overall_score(text):
    """Extract overall score from analysis text"""
    if not text:
        return None
    
    text = text.lower()
    patterns = [
        r'overall score[:\s]*(\d+\.?\d*)',
        r'total score[:\s]*(\d+\.?\d*)',
        r'final score[:\s]*(\d+\.?\d*)',
        r'score[:\s]*(\d+\.?\d*)',
        r'overall[:\s]*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*overall'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            score = match.group(1)
            return str(round(float(score), 1)) if '.' in score else score
    return None

def extract_website_description(text):
    """Extract website description from analysis text"""
    if not text:
        return "Website analysis completed"
    
    lines = text.split('\n')
    
    # Look for description patterns
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check for description indicators
        if any(indicator in line.lower() for indicator in [
            'website is for', 'the website', 'description', 'about', 'company', 'business'
        ]):
            # If line has colon, extract after it
            if ':' in line:
                desc = line.split(':', 1)[1].strip()
                if len(desc) > 15:
                    return desc[:200] + ('...' if len(desc) > 200 else '')
            
            # Check next lines for description
            for j in range(i+1, min(i+4, len(lines))):
                next_line = lines[j].strip()
                if len(next_line) > 20 and not re.search(r'score|rating|\d+\.?\d*$', next_line.lower()):
                    return next_line[:200] + ('...' if len(next_line) > 200 else '')
    
    # Fallback: get first substantial line
    for line in lines:
        line = line.strip()
        if len(line) > 30 and not re.search(r'^\d+\.?\d*$|score|rating|home|analyze', line.lower()):
            return line[:200] + ('...' if len(line) > 200 else '')
    
    return "Website analysis completed"

def extract_score_and_description(text, score_keywords, section_keywords=None):
    """Generic function to extract score and description for any criteria"""
    if not text:
        return None, ""
    
    text_lower = text.lower()
    lines = text.split('\n')
    
    # Try to find score first
    score = None
    description = ""
    
    # Score patterns - Fixed syntax
    for keyword in score_keywords:
        patterns = [
            keyword + r'[:\s]*(\d+\.?\d*)',
            keyword + r'\s*score[:\s]*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*' + keyword
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                score = match.group(1)
                if '.' in score:
                    score = str(round(float(score), 1))
                break
        if score:
            break
    
    # Find description
    if section_keywords:
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if any(keyword in line_stripped.lower() for keyword in section_keywords):
                # Look for description in next few lines
                for j in range(i, min(i+5, len(lines))):
                    desc_line = lines[j].strip()
                    if (len(desc_line) > 20 and 
                        not re.search(r'^\d+\.?\d*$|score[:\s]*\d+', desc_line.lower()) and
                        not any(skip_word in desc_line.lower() for skip_word in ['home', 'analyze', 'scoreboard'])):
                        
                        # Clean up description
                        if ':' in desc_line:
                            desc_line = desc_line.split(':', 1)[1].strip()
                        
                        description = desc_line[:120] + ('...' if len(desc_line) > 120 else '')
                        break
                if description:
                    break
    
    return score, description

def extract_audience_score(text):
    """Extract audience/consumer score"""
    score, _ = extract_score_and_description(text, ['consumer', 'audience'], ['audience perspective', 'consumer'])
    return score

def extract_audience_description(text):
    """Extract audience/consumer description"""
    _, description = extract_score_and_description(text, ['consumer', 'audience'], ['audience perspective', 'consumer'])
    return description

def extract_developer_score(text):
    """Extract developer score"""
    score, _ = extract_score_and_description(text, ['developer', 'dev'], ['developer', 'development'])
    return score

def extract_developer_description(text):
    """Extract developer description"""
    _, description = extract_score_and_description(text, ['developer', 'dev'], ['developer', 'development'])
    return description

def extract_investor_score(text):
    """Extract investor score"""
    score, _ = extract_score_and_description(text, ['investor', 'investment'], ['investor', 'investment'])
    return score

def extract_investor_description(text):
    """Extract investor description"""
    _, description = extract_score_and_description(text, ['investor', 'investment'], ['investor', 'investment'])
    return description

def extract_technical_header(text):
    """Extract technical criteria header text"""
    if not text:
        return ""
    
    lines = text.split('\n')
    for line in lines:
        if 'technical criteria' in line.lower():
            return line.strip()
    return "Technical Criteria Scores"

def extract_clarity_score(text):
    """Extract clarity score"""
    score, _ = extract_score_and_description(text, ['clarity'], ['clarity'])
    return score

def extract_clarity_description(text):
    """Extract clarity description"""
    _, description = extract_score_and_description(text, ['clarity'], ['clarity'])
    return description

def extract_visual_design_score(text):
    """Extract visual design score"""
    score, _ = extract_score_and_description(text, ['visual design', 'design', 'visual'], ['visual', 'design'])
    return score

def extract_visual_design_description(text):
    """Extract visual design description"""
    _, description = extract_score_and_description(text, ['visual design', 'design', 'visual'], ['visual', 'design'])
    return description

def extract_ux_score(text):
    """Extract UX score"""
    score, _ = extract_score_and_description(text, ['ux', 'user experience', 'usability'], ['ux', 'user experience'])
    return score

def extract_ux_description(text):
    """Extract UX description"""
    _, description = extract_score_and_description(text, ['ux', 'user experience', 'usability'], ['ux', 'user experience'])
    return description

def extract_trust_score(text):
    """Extract trust score"""
    score, _ = extract_score_and_description(text, ['trust'], ['trust'])
    return score

def extract_trust_description(text):
    """Extract trust description"""
    _, description = extract_score_and_description(text, ['trust'], ['trust'])
    return description

def extract_value_prop_score(text):
    """Extract value proposition score"""
    score, _ = extract_score_and_description(text, ['value prop', 'value'], ['value', 'proposition'])
    return score

def extract_value_prop_description(text):
    """Extract value proposition description"""
    _, description = extract_score_and_description(text, ['value prop', 'value'], ['value', 'proposition'])
    return description

# Make these functions available to templates
app.jinja_env.globals.update(
    get_company_name=get_company_name,
    extract_overall_score=extract_overall_score,
    extract_website_description=extract_website_description,
    extract_audience_score=extract_audience_score,
    extract_audience_description=extract_audience_description,
    extract_developer_score=extract_developer_score,
    extract_developer_description=extract_developer_description,
    extract_investor_score=extract_investor_score,
    extract_investor_description=extract_investor_description,
    extract_technical_header=extract_technical_header,
    extract_clarity_score=extract_clarity_score,
    extract_clarity_description=extract_clarity_description,
    extract_visual_design_score=extract_visual_design_score,
    extract_visual_design_description=extract_visual_design_description,
    extract_ux_score=extract_ux_score,
    extract_ux_description=extract_ux_description,
    extract_trust_score=extract_trust_score,
    extract_trust_description=extract_trust_description,
    extract_value_prop_score=extract_value_prop_score,
    extract_value_prop_description=extract_value_prop_description
)

# Global variable to store scraping results
scraping_results = {}
scraping_status = {}

def validate_url(url):
    """Basic URL validation"""
    if not url.strip():
        return False
    return url.strip().startswith(('http://', 'https://'))

def scrape_single_website(url, session_id, index):
    """Scrape a single website - used for parallel processing"""
    try:
        print(f"Starting scrape for {url}")
        scraper = WebsiteScraper(headless=True)
        result = scraper.scrape_single_url(url)
        
        # Update status
        with threading.Lock():
            scraping_status[session_id]['completed'] += 1
            scraping_status[session_id]['current_url'] = f"Completed {url}"
        
        print(f"Completed scrape for {url}")
        return result
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {
            'url': url,
            'status': 'error',
            'content': '',
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def start_scraping():
    """Start the scraping process - supports dynamic number of URLs"""
    data = request.get_json()
    
    # Collect all URLs dynamically (support more than 4)
    urls = []
    i = 1
    while f'url{i}' in data:
        url = data.get(f'url{i}', '').strip()
        if url:  # Only add non-empty URLs
            urls.append(url)
        i += 1
    
    # Validate URLs
    valid_urls = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invalid URL format: {url}. Please include http:// or https://'
            }), 400
    
    if not valid_urls:
        return jsonify({
            'status': 'error',
            'message': 'Please provide at least one valid URL'
        }), 400
    
    if len(valid_urls) > 10:
        return jsonify({
            'status': 'error',
            'message': 'Maximum 10 websites allowed per analysis'
        }), 400
    
    # Generate a session ID for this scraping task
    session_id = str(int(time.time()))
    
    # Initialize status
    scraping_status[session_id] = {
        'status': 'processing',
        'completed': 0,
        'total': len(valid_urls),
        'current_url': 'Starting...'
    }
    
    # Start scraping in background thread with parallel processing
    thread = threading.Thread(target=perform_parallel_scraping, args=(session_id, valid_urls))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'started',
        'session_id': session_id,
        'total_urls': len(valid_urls)
    })

def perform_parallel_scraping(session_id, urls):
    """Perform parallel scraping for faster results"""
    try:
        print(f"Starting parallel scraping for {len(urls)} URLs")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=min(len(urls), 4)) as executor:
            # Submit all scraping tasks
            future_to_url = {
                executor.submit(scrape_single_website, url, session_id, i): url 
                for i, url in enumerate(urls)
            }
            
            results = []
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"Got result for {url}")
                except Exception as e:
                    print(f"Failed to get result for {url}: {e}")
                    results.append({
                        'url': url,
                        'status': 'error',
                        'content': '',
                        'error': str(e)
                    })
        
        # Sort results by original URL order
        url_order = {url: i for i, url in enumerate(urls)}
        results.sort(key=lambda x: url_order.get(x['url'], 999))
        
        scraping_results[session_id] = results
        scraping_status[session_id]['status'] = 'completed'
        scraping_status[session_id]['current_url'] = 'All completed!'
        
        print("All scraping completed!")
        
    except Exception as e:
        print(f"Error in parallel scraping: {e}")
        scraping_status[session_id]['status'] = 'error'
        scraping_status[session_id]['error'] = str(e)

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get scraping status"""
    if session_id not in scraping_status:
        return jsonify({'status': 'not_found'}), 404
    
    return jsonify(scraping_status[session_id])

@app.route('/results/<session_id>')
def get_results(session_id):
    """Get scraping results"""
    if session_id not in scraping_results:
        return jsonify({'status': 'not_ready'}), 404
    
    return render_template('results.html', 
                         results=scraping_results[session_id],
                         session_id=session_id)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)