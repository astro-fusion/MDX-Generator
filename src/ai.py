import os
import json
import requests
from typing import Dict, List, Optional, Generator, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PerplexityAI:
    """
    A client class to interact with the Perplexity AI API.
    
    This class provides methods to make chat completion requests to Perplexity AI
    with proper error handling and response processing.
    """
    BASE_URL = "https://api.perplexity.ai"
    
    # Default models available
    DEFAULT_MODEL = "sonar-pro"
    ONLINE_MODELS = ["llama-3-sonar-large-32k-online", "sonar-medium-online", "sonar-pro"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the PerplexityAI client.

        Args:
            api_key (str, optional): Your Perplexity AI API key. 
                                   If not provided, will try to load from PERPLEXITY_API_KEY env var.
        
        Raises:
            ValueError: If no API key is found in parameters or environment variables.
        """
        # Try to get API key from parameter, then environment variable
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "API key is required. Please provide it as a parameter or set PERPLEXITY_API_KEY environment variable."
            )
        
        # Set up request headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str = DEFAULT_MODEL, 
        stream: bool = False, 
        max_tokens: int = 5000, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Makes a request to the Perplexity AI chat completions endpoint.

        Args:
            messages (List[Dict]): A list of message objects with 'role' and 'content' keys.
            model (str): The model to use for generation.
            stream (bool): Whether to stream the response (not fully implemented).
            max_tokens (int): Maximum tokens for the response.
            **kwargs: Additional parameters (temperature, web_search_options, etc.).

        Returns:
            Dict[str, Any]: The JSON response from the API or error structure.
        """
        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # Remove None values to avoid API issues
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            # Make API request
            response = requests.post(
                f"{self.BASE_URL}/chat/completions", 
                headers=self.headers, 
                json=payload,
                timeout=60  # Add timeout for better error handling
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code}: {e}"
            # Try to get error details from response
            try:
                error_details = response.json()
                error_msg = error_details.get('error', {}).get('message', error_msg)
            except:
                pass
            return self._create_error_response(error_msg, "http_error")
            
        except requests.exceptions.Timeout:
            return self._create_error_response("Request timed out", "timeout_error")
            
        except requests.exceptions.ConnectionError:
            return self._create_error_response("Connection error", "connection_error")
            
        except requests.exceptions.RequestException as e:
            return self._create_error_response(str(e), "api_connection_error")
            
        except json.JSONDecodeError:
            error_msg = f"Failed to decode API response. Status: {response.status_code}"
            return self._create_error_response(error_msg, "invalid_response_error")

    def _create_error_response(self, message: str, error_type: str) -> Dict[str, Any]:
        """
        Creates a standardized error response structure.
        
        Args:
            message (str): Error message
            error_type (str): Type of error
            
        Returns:
            Dict[str, Any]: Standardized error response
        """
        return {
            "error": {
                "message": message,
                "type": error_type
            }
        }


# Initialize the client (will load API key from environment)
try:
    aiClient = PerplexityAI()
except ValueError as e:
    print(f"Warning: {e}")
    aiClient = None


def call_perplexity_chat(
    messages: List[Dict[str, str]], 
    model: str = "sonar-pro", 
    stream: bool = False, 
    max_tokens: int = 5000, 
    **kwargs
) -> Generator[str, None, None]:
    """
    Helper function to make a chat completion request to the Perplexity AI API.
    
    This function handles the API response and formats it with sources if available.
    
    Args:
        messages (List[Dict]): Chat messages
        model (str): Model to use
        stream (bool): Whether to stream (not fully implemented)
        max_tokens (int): Maximum response tokens
        **kwargs: Additional API parameters
        
    Yields:
        str: Generated content with sources appended
    """
    if not aiClient:
        yield "Error: Perplexity AI client not initialized. Check your API key configuration."
        return

    try:
        if stream:
            # TODO: Implement proper streaming response handling
            yield "Error: Streaming response handling is not fully implemented."
            return

        # Make API request
        response = aiClient.chat(
            messages=messages,
            model=model,
            stream=False,
            max_tokens=max_tokens,
            **kwargs
        )

        # Check for API errors
        if response.get('error'):
            error_msg = response['error'].get('message', 'Unknown API error')
            yield f"API Error: {error_msg}"
            return

        # Extract content and sources from response
        ai_content, sources = _extract_response_data(response)
        
        # Build final content with sources
        final_content = _build_content_with_sources(ai_content, sources)
        
        if final_content:
            yield final_content
        else:
            yield "Error: No content generated from API response."

    except Exception as e:
        yield f"Error calling Perplexity API: {str(e)}"


def _extract_response_data(response: Dict[str, Any]) -> tuple[str, Optional[List[Dict]]]:
    """
    Extracts content and sources from API response.
    
    Args:
        response (Dict): API response
        
    Returns:
        Tuple[str, Optional[List[Dict]]]: Content and sources
    """
    ai_content = ""
    sources = None
    
    # Extract main content
    if response.get('choices') and response['choices']:
        choice = response['choices'][0]
        message = choice.get('message', {})
        ai_content = message.get('content', '')
        
        # Extract sources from choice or response root
        sources = choice.get('sources') or response.get('sources')
    
    return ai_content, sources


def _build_content_with_sources(content: str, sources: Optional[List[Dict]]) -> str:
    """
    Builds final content with sources section.
    
    Args:
        content (str): Main AI-generated content
        sources (Optional[List[Dict]]): List of source objects
        
    Returns:
        str: Content with sources section appended
    """
    content_parts = []
    
    # Add sources section if available
    if sources:
        resources_section = "\n\n## Resources\n"
        for i, source in enumerate(sources, 1):
            title = source.get('title', source.get('url', 'Unknown Source'))
            url = source.get('url')
            
            if url:
                resources_section += f"{i}. [{title}]({url})\n"
            else:
                resources_section += f"{i}. {title}\n"
        
        resources_section += "\n"
        content_parts.append(resources_section)
    
    # Add main content
    if content:
        content_parts.append(content)
    
    return "".join(content_parts)


def generate_blog(
    title: str, 
    description: str, 
    template_content: str, 
    knowledge_text: str
) -> Generator[str, None, None]:
    """
    Generate SEO-friendly blog content using the Perplexity AI API.
    
    This function creates a comprehensive blog post based on the provided title,
    description, template, and knowledge base.
    
    Args:
        title (str): Blog post title and primary keyword
        description (str): Description of what the article should cover
        template_content (str): Markdown template to follow
        knowledge_text (str): Additional knowledge base information
        
    Yields:
        str: Generated blog content
    """
    # Build comprehensive prompt for SEO-optimized content
    prompt = _build_blog_prompt(title, description, template_content, knowledge_text)
    
    # Prepare messages for API
    messages = [
        {
            "role": "system", 
            "content": (
                "You are an expert Astrologer and SEO content writer, specialized in creating "
                "in-depth, engaging, and SEO-optimized markdown blog content. You strictly follow "
                "user instructions for structure and content. IMPORTANT: Include at least 3-5 "
                "relevant external sources with full URLs in markdown format [Title](URL) in a Resources section."
            )
        },
        {"role": "user", "content": prompt}
    ]

    # Configure web search for better content quality
    web_search_options = {
        "search_context_size": "high"  # Options: low, medium, high
    }

    # Generate content using the helper function
    yield from call_perplexity_chat(
        messages=messages,
        model="sonar-pro",  # Use online model for web search capabilities
        max_tokens=5000,
        stream=False,
        web_search_options=web_search_options
    )


def _build_blog_prompt(
    title: str, 
    description: str, 
    template_content: str, 
    knowledge_text: str
) -> str:
    """
    Builds the comprehensive prompt for blog generation.
    
    Args:
        title (str): Blog post title
        description (str): Blog post description
        template_content (str): Template to follow
        knowledge_text (str): Knowledge base content
        
    Returns:
        str: Complete prompt for AI generation
    """
    return f"""
You are tasked with generating the main body content for an SEO-friendly blog post on the topic: "{title}".
The primary keyword for this article is "{title}".
The article should elaborate on the following aspects: "{description}".

You MUST strictly follow the structure and headings provided in the Markdown template below to generate the article body.
Fill in each section of the template with comprehensive, engaging, and unique content.
DO NOT include any '---' frontmatter blocks or YAML frontmatter (like 'title:', 'description:', 'keywords:') in your output.
Your output should start directly with the H1 heading (e.g., '# {title}: Understanding Its Role in Vedic Astrology').

SEO and Content Guidelines for the Article Body:
1.  **Primary Keyword Usage**: Naturally integrate the primary keyword "{title}" throughout the article, especially in the introduction, some headings (H2, H3), and the conclusion. Avoid keyword stuffing.
2.  **Content Structure**: Use the headings (H1, H2, H3, etc.) as defined in the template. Ensure headings are descriptive and incorporate keywords where it makes sense.
3.  **Readability**: Write in clear, concise language. Use short sentences and paragraphs. Employ bullet points or numbered lists for clarity where appropriate.
4.  **Engagement**: Make the content informative and engaging for readers interested in Vedic Astrology.
5.  **Unique Content**: Ensure the generated content is original and provides value.
6.  **Citations**: If you use external information, cite your sources clearly within the text (e.g., [1], [2]).
7.  **Template Adherence**: Populate all sections of the provided template for the article body.

Template for the article body (starts with H1 heading):
```markdown
{template_content}
```

Additional Information (Knowledge Base):
{knowledge_text}

Based on all the above, generate the complete Markdown blog post body content now, starting with the H1 heading:
"""


# Utility function to check if API key is configured
def is_api_configured() -> bool:
    """
    Check if the Perplexity API is properly configured.
    
    Returns:
        bool: True if API key is available, False otherwise
    """
    return aiClient is not None and aiClient.api_key is not None
