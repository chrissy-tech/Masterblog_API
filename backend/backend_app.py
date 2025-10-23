from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import math
from datetime import datetime, date
from flask_swagger_ui import get_swaggerui_blueprint
from pathlib import Path

# --- CONSTANTS AND CONFIGURATION ---

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "Frontend" / "static"
JSON_FILE_PATH = BASE_DIR / "posts.json"

# Swagger UI configuration constants
SWAGGER_URL = "/api/docs"
API_URL = "/static/masterblog.json"

# Default data structure
DEFAULT_POSTS = [
    {
        "id": 1,
        "title": "First post about Python",
        "content": (
            "This is the first post. Python is great."
        ),
        "author": "Alice Python",
        "date": "2024-05-15",
    },
    {
        "id": 2,
        "title": "Second post about Flask",
        "content": (
            "This is the second post. Flask makes APIs easy."
        ),
        "author": "Bob Flask",
        "date": "2024-05-20",
    },
]

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# --- SWAGGER UI SETUP ---

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "Masterblog API"
    },
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

def load_posts():
    """
    Loads blog posts from the JSON file. If the file is missing or empty,
    it initializes it with DEFAULT_POSTS.
    """
    if not JSON_FILE_PATH.exists():
        # If the file doesn't exist, create it with the initial data
        save_posts(DEFAULT_POSTS)
        return DEFAULT_POSTS

    try:
        content = JSON_FILE_PATH.read_text()
        if not content:
            return []
        return json.loads(content)
    except json.JSONDecodeError:
        return []


def save_posts(posts):
    """Saves the current list of posts back to the JSON file."""
    JSON_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_FILE_PATH.write_text(json.dumps(posts, indent=4))


def get_new_id():
    """Returns the next available unique ID based on the current posts."""
    posts = load_posts()
    return max(post["id"] for post in posts) + 1 if posts else 1


def add_post(data):
    """
    Internal function to create, timestamp, and save a new post object.
    """
    new_post = {
        "id": get_new_id(),
        "title": data.get("title"),
        "content": data.get("content"),
        # Add new fields. Use today's date if date is missing.
        "author": data.get("author", "Anonymous"),
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
    }

    current_posts = load_posts()
    current_posts.append(new_post)
    save_posts(current_posts)

    return new_post


# Global list loaded on startup
POSTS = load_posts()

# --- API ENDPOINTS (Routes) ---

@app.route("/api/posts", methods=["GET", "POST"])
def handle_posts():
    """
    Handles GET (Read, Sort, Paginate) and POST (Create) requests
    for blog posts.
    """
    global POSTS
    # Ensure posts are loaded (important for concurrent access simulation)
    POSTS = load_posts()

    if request.method == "POST":
        data = request.json

        if not data or "title" not in data or "content" not in data:
            return (
                jsonify({"error":
							 "Missing title or content in request body."}),
                400,
            )

        # The add_post logic handles ID, author, and date
        new_post = add_post(data)
        return jsonify(new_post), 201

    # --- GET Logic (Read, Sort, Paginate) ---
    if request.method == "GET":
        """
        Returns all blog posts, with optional sorting and pagination
        functionality via query parameters.
        """
        sort_by = request.args.get("sort")
        direction = request.args.get("direction")

        # Initialize the list of posts to be processed
        posts_list = POSTS

        # ID added here:
        valid_sort_fields = ["id", "title", "content", "author", "date"]

        # --- Sorting Logic ---
        if sort_by or direction:
            # 1.1 Handle incomplete sorting parameters
            if (sort_by and not direction) or (direction and not sort_by):
                return (
                    jsonify(
                        {
                            "error": (
                                "Both 'sort' and 'direction' query"
								" parameters must be provided for sorting."
                            )
                        }
                    ),
                    400,
                )

            # Handle invalid parameters
            if sort_by not in valid_sort_fields:
                return (
                    jsonify(
                        {
                            "error": (
                                f"Invalid sort field. Must be one of: "
                                f"{', '.join(valid_sort_fields)}"
                            )
                        }
                    ),
                    400,
                )
            if direction not in ["asc", "desc"]:
                return (
                    jsonify(
                        {
                            "error": (
                                "Invalid sort direction. Must be 'asc' or "
                                "'desc'."
                            )
                        }
                    ),
                    400,
                )

            # Apply sorting
            is_reverse = direction == "desc"

            if sort_by == "date":

                def date_sort_key(post):
                    """
                    Converts post date string to date object for sorting.
                    """
                    date_str = post.get("date", "1900-01-01")
                    try:
                        return datetime.strptime(
                            date_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        # If date format is invalid, treat as very old
                        return date(1900, 1, 1)

                posts_list = sorted(
                    POSTS, key=date_sort_key, reverse=is_reverse
                )
            elif sort_by == "id":
                # Sort numerically by ID (THIS FIXES THE CRASH)
                posts_list = sorted(
                    POSTS, key=lambda post: post.get("id", 0),
					reverse=is_reverse
                )
            else:
                # Standard string sorting for title, content, author
                posts_list = sorted(
                    POSTS,
                    key=lambda post: str(post.get(sort_by, "")).lower(),
                    reverse=is_reverse,
                )

        #--- Pagination Logic ---
        page = request.args.get("page")
        per_page = request.args.get("per_page")

        # Check if ANY sorting or pagination parameters are present
        if sort_by or direction or page or per_page:
            # Default page to 1 if sorting is present but page isn't
            if page is None:
                page = 1

            # Default per_page to the total length if not provided
            if per_page is None:
                per_page = len(posts_list) if posts_list else 10

            try:
                # Convert to integers and ensure positive values
                page = int(page)
                per_page = int(per_page)
            except ValueError:
                return (
                    jsonify(
                        {
                            "error": (
                                "Pagination parameters 'page' and 'per_page' "
                                "must be valid integers."
                            )
                        }
                    ),
                    400,
                )

            if page < 1 or per_page < 1:
                return (
                    jsonify(
                        {
                            "error": (
                                "Pagination parameters 'page' and 'per_page' "
                                "must be positive integers."
                            )
                        }
                    ),
                    400,
                )

            # Calculate indices and slice
            total_posts = len(posts_list)
            # Use math.ceil to calculate total pages correctly
            total_pages = math.ceil(total_posts / per_page) \
                if per_page > 0 else 0

            start_index = (page - 1) * per_page
            end_index = start_index + per_page

            # Slice the list for the current page
            paginated_posts = posts_list[start_index:end_index]

            # Return structured, paginated results
            return jsonify(
                {
                    "total_posts": total_posts,
                    "total_pages": total_pages,
                    "current_page": page,
                    "per_page": per_page,
                    "results": paginated_posts,
                }
            )

        #--- Default: Return plain list if NO query parameters ---
        return jsonify(POSTS)


@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    """Deletes a post by its ID from the posts list and file."""
    global POSTS
    # Ensure working with latest data
    POSTS = load_posts()

    post_to_delete = None
    for post in POSTS:
        if post["id"] == post_id:
            post_to_delete = post
            break

    # Error Handling: If post is not found
    if post_to_delete is None:
        return (
            jsonify({"error": f"Post with id {post_id} not found."}),
            404,
        )

    # Delete the post from the list and SAVE to file
    POSTS.remove(post_to_delete)
    save_posts(POSTS)

    return (
        jsonify(
            {
                "message": (
                    f"Post with id {post_id} has been deleted successfully."
                )
            }
        ),
        200,
    )


@app.route("/api/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    """
    Updates an existing post by its ID with optional title, content,
    author, or date changes.
    """
    global POSTS
    # Ensure working with latest data
    POSTS = load_posts()

    # Find the post's index to allow direct modification
    post_index = -1
    for i, post in enumerate(POSTS):
        if post["id"] == post_id:
            post_index = i
            break

    # Error Handling: If post is not found
    if post_index == -1:
        return (
            jsonify({"error": f"Post with id {post_id} not found."}),
            404,
        )

    # Retrieve JSON data and update the post
    data = request.get_json()
    post_to_update = POSTS[post_index]

    # Track if any changes were made
    changes_made = False

    if data:
        # Update fields
        if (
            "title" in data
            and post_to_update["title"] != data["title"]
        ):
            post_to_update["title"] = data["title"]
            changes_made = True
        if (
            "content" in data
            and post_to_update["content"] != data["content"]
        ):
            post_to_update["content"] = data["content"]
            changes_made = True
        if (
            "author" in data
            and post_to_update.get("author") != data["author"]
        ):
            post_to_update["author"] = data["author"]
            changes_made = True
        if (
            "date" in data
            and post_to_update.get("date") != data["date"]
        ):
            post_to_update["date"] = data["date"]
            changes_made = True

    # SAVE to file if changes were made
    if changes_made:
        save_posts(POSTS)

    # Return the fully updated post object
    return jsonify(post_to_update), 200


@app.route("/api/posts/search", methods=["GET"])
def search_posts():
    """
    Searches for blog posts based on a single query parameter ('query')
    across title, content, author, and date fields.
    Returns a structured JSON response with count, results, and a message.
    """
    global POSTS
    # Ensure working with latest data
    POSTS = load_posts()

    # Get all query parameters from the URL
    search_term = request.args.get("query", "").lower()

    # If no search terms are provided, return all posts
    if not search_term:
        # Return all posts wrapped in the new structured format for consistency
        return jsonify(
            {
                "count": len(POSTS),
                "results": POSTS,
                "message": f"{len(POSTS)} results found.",
            }
        )

    results = [
        post
        for post in POSTS
        # Check if the search term is in title, content, author, OR date
        if (
            (search_term in post.get("title", "").lower())
            or (search_term in post.get("content", "").lower())
            or (search_term in post.get("author", "").lower())
            or (search_term in post.get("date", "").lower())
        )
    ]

    # Prepare structured response with the count and message
    count = len(results)

    if count == 0:
        message = "0 results found."
    elif count == 1:
        message = "1 result found."
    else:
        message = f"{count} results found."

    # Return the structured response
    return jsonify({"count": count, "results": results, "message": message})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)