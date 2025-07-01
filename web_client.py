import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re


class WebClient:
    def __init__(self, output_dir, aggressive_html_cleaning=False):
        """
        Initialize WebClient with output directory and HTML cleaning option.
        
        Args:
            output_dir (str): Directory where webpage files will be saved
            aggressive_html_cleaning (bool): Whether to perform aggressive HTML cleaning
        """
        self.output_dir = output_dir
        self.aggressive_html_cleaning = aggressive_html_cleaning
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _get_filename_from_url(self, url, extension):
        """
        Generate a safe filename from URL.
        
        Args:
            url (str): The URL to convert to filename
            extension (str): File extension to append
            
        Returns:
            str: Safe filename
        """
        parsed = urlparse(url)
        # Use domain and path to create filename
        filename = f"{parsed.netloc}{parsed.path}".replace('/', '_').replace('\\', '_').replace('.', '_').replace('+', '_')
        # Remove invalid characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        # Remove trailing dots and spaces
        filename = filename.strip('. ')
        # Ensure filename isn't empty
        if not filename:
            filename = "webpage"
        
        return f"{filename[-16:]}.{extension}"
    
    def _aggressive_clean_html(self, soup: BeautifulSoup):
        """
        Perform aggressive HTML cleaning to remove non-content elements.
        
        Args:
            soup (BeautifulSoup): BeautifulSoup object to clean
        """
        # Remove script and style elements completely
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
        
        # Remove structural/navigation elements
        structural_tags = [
            "nav", "header", "footer", "aside", "menu", "menuitem",
            "toolbar", "banner", "complementary", "contentinfo",
            "navigation", "search"
        ]
        for tag in structural_tags:
            for element in soup.find_all(tag):
                if element is not None:
                    element.decompose()
        
        # Remove elements by common class/id patterns for ads, social, etc.
        ad_patterns = [
            # Ad-related
            r'.*ad[s]?[-_].*', r'.*advertisement.*', r'.*banner.*', r'.*sponsor.*',
            r'.*promo.*', r'.*commercial.*', r'.*marketing.*',
            # Social media
            r'.*social.*', r'.*share.*', r'.*facebook.*', r'.*twitter.*', 
            r'.*linkedin.*', r'.*instagram.*', r'.*youtube.*', r'.*pinterest.*',
            # Navigation and UI
            r'.*nav.*', r'.*menu.*', r'.*sidebar.*', r'.*header.*', r'.*footer.*',
            r'.*breadcrumb.*', r'.*pagination.*', r'.*pager.*',
            # Comments and interactions
            r'.*comment.*', r'.*reply.*', r'.*discussion.*', r'.*feedback.*',
            # Widgets and extras
            r'.*widget.*', r'.*plugin.*', r'.*popup.*', r'.*modal.*', r'.*overlay.*',
            r'.*newsletter.*', r'.*subscribe.*', r'.*signup.*', r'.*login.*',
            # Related/recommended content
            r'.*related.*', r'.*recommend.*', r'.*suggest.*', r'.*similar.*',
            r'.*more.*stories.*', r'.*trending.*', r'.*popular.*',
            # Metadata and tracking
            r'.*meta.*', r'.*track.*', r'.*analytics.*', r'.*pixel.*',
            # Cookie and privacy
            r'.*cookie.*', r'.*privacy.*', r'.*gdpr.*', r'.*consent.*'
        ]
        
        # Compile regex patterns for efficiency
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ad_patterns]
        
        # Remove elements with matching class or id attributes
        for element in soup.find_all(attrs={"class": True}):
            try: 
                classes = ' '.join(element.get('class', []))
                if any(pattern.search(classes) for pattern in compiled_patterns):
                    element.decompose()
                    continue
            except (AttributeError, ValueError, TypeError) as e:
                continue
        
        for element in soup.find_all(attrs={"id": True}):
            try:
                element_id = element.get('id', '')
                if any(pattern.search(element_id) for pattern in compiled_patterns):
                    element.decompose()
                    continue
            except (AttributeError, ValueError, TypeError) as e:
                continue
        
        # Remove elements with specific roles
        unwanted_roles = [
            "banner", "navigation", "complementary", "contentinfo", 
            "search", "form", "dialog", "alertdialog", "menu", "menubar"
        ]
        for role in unwanted_roles:
            for element in soup.find_all(attrs={"role": role}):
                element.decompose()
        
        # Remove form elements (usually for search, login, newsletter)
        form_elements = ["form", "input", "button", "select", "textarea", "fieldset"]
        for tag in form_elements:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove iframe, embed, object (often ads or external content)
        media_elements = ["iframe", "embed", "object", "applet"]
        for tag in media_elements:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements that are likely ads based on size attributes
        for element in soup.find_all(attrs={"width": True, "height": True}):
            try:
                width = int(re.search(r'\d+', str(element.get('width', '0'))).group())
                height = int(re.search(r'\d+', str(element.get('height', '0'))).group())
                # Common ad sizes
                ad_sizes = [
                    (728, 90), (300, 250), (336, 280), (320, 50), (468, 60),
                    (970, 250), (300, 600), (320, 100), (970, 90), (160, 600)
                ]
                if (width, height) in ad_sizes:
                    element.decompose()
            except (AttributeError, ValueError):
                pass
        
        # Remove comments
        from bs4 import Comment
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        
        # Remove elements with very little text content (likely decorative)
        for element in soup.find_all():
            if element.name in ['div', 'span', 'section', 'article']:
                text_content = element.get_text(strip=True)
                # Remove if element has no text or only whitespace/symbols
                if not text_content or len(text_content) < 3:
                    # But keep if it has meaningful child elements
                    meaningful_children = element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th'])
                    if not meaningful_children:
                        element.decompose()
        
        # Remove empty elements after cleaning
        for element in soup.find_all():
            if not element.get_text(strip=True) and not element.find_all(['img', 'video', 'audio']):
                element.decompose()
    
    def get_webpage_file(self, url):
        """
        Download and save the file that the URL is pointing to.
        If it's HTML, clean and save as HTML. If it's PDF or other file types, download directly.
        
        Args:
            url (str): URL of the file to download
        
        Returns:
            tuple: (response, content) where content is the file content or error message
        """
        try:
            # Browser headers to avoid bot filters
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Send HEAD request first to check content type
            head_response = requests.head(url, headers=headers, timeout=30, allow_redirects=True, verify=False)
            content_type = head_response.headers.get('content-type', '').lower()
            
            # Send GET request
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # Update content type from actual response if not available from HEAD
            if not content_type:
                content_type = response.headers.get('content-type', '').lower()
            
            # Determine file type and extension
            if 'text/html' in content_type or 'application/xhtml' in content_type:
                # Handle HTML content
                html_content = response.text
                
                # Apply HTML cleaning if aggressive cleaning is enabled
                if self.aggressive_html_cleaning:
                    # Parse HTML with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Remove non-main content elements first
                    self._remove_non_main_content(soup)
                    
                    # Apply aggressive cleaning
                    self._aggressive_clean_html(soup)
                    
                    # Convert back to HTML string
                    html_content = str(soup)

                # remove html extension if present
                url = url.replace('.html', '') if url.endswith('.html') else url
                
                # Generate filename and save
                filename = self._get_filename_from_url(url, 'html')
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"HTML saved to: {filepath}")
                return (response, html_content)
                
            else:
                # Handle non-HTML files (PDF, images, documents, etc.)
                # Determine appropriate file extension
                extension = 'bin'  # default binary extension
                
                if 'application/pdf' in content_type:
                    extension = 'pdf'
                elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                    extension = 'jpg'
                elif 'image/png' in content_type:
                    extension = 'png'
                elif 'image/gif' in content_type:
                    extension = 'gif'
                elif 'image/webp' in content_type:
                    extension = 'webp'
                elif 'image/svg' in content_type:
                    extension = 'svg'
                elif 'application/msword' in content_type:
                    extension = 'doc'
                elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                    extension = 'docx'
                elif 'application/vnd.ms-excel' in content_type:
                    extension = 'xls'
                elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                    extension = 'xlsx'
                elif 'application/vnd.ms-powerpoint' in content_type:
                    extension = 'ppt'
                elif 'application/vnd.openxmlformats-officedocument.presentationml.presentation' in content_type:
                    extension = 'pptx'
                elif 'text/plain' in content_type:
                    extension = 'txt'
                elif 'text/csv' in content_type:
                    extension = 'csv'
                elif 'application/json' in content_type:
                    extension = 'json'
                elif 'application/xml' in content_type or 'text/xml' in content_type:
                    extension = 'xml'
                elif 'application/zip' in content_type:
                    extension = 'zip'
                elif 'application/x-rar' in content_type:
                    extension = 'rar'
                elif 'application/x-7z-compressed' in content_type:
                    extension = '7z'
                elif 'video/mp4' in content_type:
                    extension = 'mp4'
                elif 'video/avi' in content_type:
                    extension = 'avi'
                elif 'audio/mpeg' in content_type:
                    extension = 'mp3'
                elif 'audio/wav' in content_type:
                    extension = 'wav'
                
                # Try to extract extension from URL if content-type detection failed
                if extension == 'bin':
                    parsed_url = urlparse(url)
                    url_path = parsed_url.path
                    if '.' in url_path:
                        url_extension = url_path.split('.')[-1].lower()
                        # Validate it's a reasonable extension (alphanumeric, max 5 chars)
                        if re.match(r'^[a-zA-Z0-9]{1,5}$', url_extension):
                            extension = url_extension

                url = url.replace(f'.{extension}', '') if url.endswith(f'.{extension}') else url
                
                # Generate filename and save binary content
                filename = self._get_filename_from_url(url, extension)
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"File saved to: {filepath}")
                return (response, f"Binary file saved as {filename}")
                
        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return (f"Error downloading file: {e}", "")
        except IOError as e:
            print(f"Error saving file: {e}")
            return (f"Error saving file: {e}", "")
    
    def get_webpage_text(self, url):
        """
        Download webpage and save only the extracted text content.
        
        Args:
            url (str): URL of the webpage to download
            
        Returns:
            str: Content of the saved text file
        """
        try:
            # Browser headers to avoid bot filters
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Send GET request
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove non-main content elements first
            self._remove_non_main_content(soup)

            
            if self.aggressive_html_cleaning:
                self._aggressive_clean_html(soup)
            else:
                # Basic cleaning - just remove script and style tags
                for script in soup(["script", "style"]):
                    script.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Generate filename and full path
            filename = self._get_filename_from_url(url, 'txt')
            filepath = os.path.join(self.output_dir, filename)
            
            # Save text content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"Text saved to: {filepath}")
            return (response, text)
            
        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return (f"Error downloading webpage: {e}", "")
        except IOError as e:
            print(f"Error saving file: {e}")
            return (f"Error downloading webpage: {e}", "")

    def _remove_non_main_content(self, soup: BeautifulSoup) -> None:
        """
        Remove elements that are not likely to be part of the main text content.
        
        Args:
            soup (BeautifulSoup): BeautifulSoup object to clean
        """
        # Remove structural elements that typically contain non-main content
        structural_selectors = [
            'nav', 'header', 'footer', 'aside', 'sidebar',
            '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]', '[role="complementary"]',
            '.sidebar', '.nav', '.navigation', '.header', '.footer', '.aside',
            '#sidebar', '#nav', '#navigation', '#header', '#footer', '#aside'
        ]

        
        for selector in structural_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element:
                    element.decompose()
        
        # Find potential main content area
        main_content = self._find_main_content_area(soup)
        
        if main_content:
            # Find the article title/heading
            title_element = self._find_article_title(main_content)
            
            if title_element:
                # Remove all elements that appear before the title
                self._remove_elements_before_title(main_content, title_element)
        
        # Remove common non-content elements by class/id patterns
        non_content_patterns = [
            r'.*breadcrumb.*', r'.*pagination.*', r'.*pager.*', r'.*tags.*',
            r'.*author.*info.*', r'.*byline.*', r'.*meta.*', r'.*date.*',
            r'.*share.*', r'.*social.*', r'.*related.*', r'.*recommend.*',
            r'.*comment.*', r'.*reply.*', r'.*discussion.*'
        ]
        
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in non_content_patterns]
        
        # Remove by class - create a copy of the list to avoid modification during iteration
        elements_with_class = list(soup.find_all(attrs={"class": True}))
        for element in elements_with_class:
            try:
                if element and element.parent:  # Check if element still exists and has parent
                    classes = element.get('class', [])
                    if classes:
                        classes_str = ' '.join(classes)
                        if any(pattern.search(classes_str) for pattern in compiled_patterns):
                            element.decompose()
            except (AttributeError, TypeError):
                continue

        # Remove by id - create a copy of the list to avoid modification during iteration
        elements_with_id = list(soup.find_all(attrs={"id": True}))
        for element in elements_with_id:
            try:
                if element and element.parent:  # Check if element still exists and has parent
                    element_id = element.get('id', '')
                    if element_id and any(pattern.search(element_id) for pattern in compiled_patterns):
                        element.decompose()
            except (AttributeError, TypeError):
                continue

    def _find_main_content_area(self, soup):
        """
        Attempt to find the main content area of the webpage.
        
        Args:
            soup (BeautifulSoup): BeautifulSoup object to search
            
        Returns:
            BeautifulSoup element or None: Main content area if found
        """
        # Try semantic HTML5 main element first
        main = soup.find('main')
        if main:
            return main
        
        # Try article element
        article = soup.find('article')
        if article:
            return article
        
        # Try role="main"
        main_role = soup.find(attrs={"role": "main"})
        if main_role:
            return main_role
        
        # Try common main content selectors
        main_selectors = [
            '#main', '#content', '#main-content', '#primary', '#article',
            '.main', '.content', '.main-content', '.primary', '.article',
            '.post', '.entry', '.story'
        ]
        
        for selector in main_selectors:
            element = soup.select_one(selector)
            if element:
                return element
        
        # If nothing found, return the body or the whole soup
        return soup.find('body') or soup

    def _find_article_title(self, content_area):
        """
        Find the main article title/heading within the content area.
        
        Args:
            content_area (BeautifulSoup element): Main content area to search
            
        Returns:
            BeautifulSoup element or None: Title element if found
        """
        # Look for h1 first (most likely to be the main title)
        h1 = content_area.find('h1')
        if h1:
            return h1
        
        # Try other heading levels
        for level in ['h2', 'h3', 'h4']:
            heading = content_area.find(level)
            if heading:
                return heading
        
        # Try elements with title-like classes
        title_selectors = [
            '.title', '.headline', '.post-title', '.entry-title', '.article-title',
            '[class*="title"]', '[class*="headline"]'
        ]
        
        for selector in title_selectors:
            element = content_area.select_one(selector)
            if element:
                return element
        
        return None

    def _remove_elements_before_title(self, content_area, title_element):
        """
        Remove all elements that appear before the title element in the DOM.
        
        Args:
            content_area (BeautifulSoup element): Main content area
            title_element (BeautifulSoup element): The title element
        """
        # Get all elements before the title
        current = content_area.find()
        while current and current != title_element:
            next_element = current.find_next_sibling() or current.find_next()
            
            # Check if current element contains the title
            if title_element in current.find_all():
                break
            
            # Remove the element if it's not the title or doesn't contain it
            if current != title_element and title_element not in current.find_all():
                current.decompose()
            
            current = next_element
