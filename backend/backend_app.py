from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Allows cross-origin access

JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'posts.json')

# --- Initial Data Structure (Used only if the JSON file is not found) ---
INITIAL_POSTS = [
	{"id": 1, "title": "First post about Python", "content": "This is the first post. Python is great."},
	{"id": 2, "title": "Second post about Flask", "content": "This is the second post. Flask makes APIs easy."},
]

def load_posts():
	"""Loads blog posts from the JSON file."""
	if not os.path.exists(JSON_FILE):
		# If the file doesn't exist, create it with the initial data
		save_posts(INITIAL_POSTS)
		return INITIAL_POSTS

	try:
		with open(JSON_FILE, 'r') as f:
			content = f.read()
			if not content:
				return []
			return json.loads(content)
	except json.JSONDecodeError:
		print(f"Error decoding JSON from {JSON_FILE}. Initializing with empty list.")
		return []

def save_posts(posts):
	"""Saves the current list of posts back to the JSON file."""
	os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
	with open(JSON_FILE, 'w') as f:
		json.dump(posts, f, indent=4)

POSTS = load_posts()

def get_new_id(posts):
	"""Returns the next available unique ID."""
	return max(post['id'] for post in posts) + 1 if posts else 1

@app.route('/api/posts', methods=['GET'])
def get_posts():
	"""
	Returns all blog posts, with optional sorting functionality
	via query parameters.
	Sorts by 'title' or 'content' in 'asc' (ascending)
	 or 'desc' (descending) order.
	"""
	sort_by = request.args.get('sort')
	direction = request.args.get('direction')

	valid_sort_fields = ['title', 'content']

	# Handle case where one parameter is provided without the other
	if (sort_by and not direction) or (direction and not sort_by):
		return jsonify({"error": "Both 'sort' and 'direction' query"
								 "parameters must be provided"
								 "for sorting."}), 400

	# Handle invalid 'sort' field
	if sort_by and sort_by not in valid_sort_fields:
		return jsonify({"error": f"Invalid sort field. Must be one of:"
								 f" {', '.join(valid_sort_fields)}"}), 400

	# Handle invalid 'direction'
	if direction and direction not in ['asc', 'desc']:
		return jsonify({"error": "Invalid sort direction. "
								 "Must be 'asc' or 'desc'."}), 400

	# Apply sorting if both are valid and present
	if sort_by and direction:
		is_reverse = (direction == 'desc')

		sorted_posts = sorted(
			POSTS,
			key=lambda post: str(post.get(sort_by, '')).lower(),
			reverse=is_reverse
		)
		return jsonify(sorted_posts)

	# Default: Return original order
	return jsonify(POSTS)


@app.route('/api/posts', methods=['POST'])
def add_post():
	"""Creates a new blog post from JSON data."""
	data = request.get_json()

	# Error Handling: Check if 'title' and 'content' are provided
	if not data or 'title' not in data or 'content' not in data:
		return jsonify({
			"error": "Missing required fields",
			"required": ["title", "content"]
		}), 400  # HTTP 400 Bad Request

	# Generate ID and create the new post object
	new_id = get_new_id(POSTS)

	new_post = {
		"id": new_id,
		"title": data['title'],
		"content": data['content']
	}

	# Add the post to the list and SAVE to file
	POSTS.append(new_post)
	save_posts(POSTS) # Save changes to posts.json

	return jsonify(new_post), 201


@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
	"""Deletes a post by its ID from the in-memory list."""
	global POSTS

	post_to_delete = None
	for post in POSTS:
		if post['id'] == id:
			post_to_delete = post
			break

	# Error Handling: If post is not found
	if post_to_delete is None:
		return jsonify({"error": f"Post with id {id} not found."}), 404

	# Delete the post from the list and SAVE to file
	POSTS.remove(post_to_delete)
	save_posts(POSTS)

	return jsonify({
		"message": f"Post with id {id} has been deleted successfully."
	}), 200

# --- PUT ENDPOINT (Update) ---
@app.route('/api/posts/<int:id>', methods=['PUT'])
def update_post(id):
	"""Updates an existing post by its
	ID with optional title/content changes.
	"""
	global POSTS

	# Find the post's index to allow direct modification
	post_index = -1
	for i, post in enumerate(POSTS):
		if post['id'] == id:
			post_index = i
			break

	# Error Handling: If post is not found
	if post_index == -1:
		return jsonify({"error": f"Post with id {id} not found."}), 404

	# Retrieve JSON data and update the post
	data = request.get_json()
	post_to_update = POSTS[post_index]

	# Track if any changes were made
	changes_made = False

	if data:
		if 'title' in data and post_to_update['title'] != data['title']:
			post_to_update['title'] = data['title']
			changes_made = True
		if 'content' in data and post_to_update['content'] != data['content']:
			post_to_update['content'] = data['content']
			changes_made = True

	# SAVE to file if changes were made
	if changes_made:
		save_posts(POSTS)

	# Return the fully updated post object
	return jsonify(post_to_update), 200


@app.route('/api/posts/search', methods=['GET'])
def search_posts():
	"""
	Searches for blog posts based on query parameters (title and/or content).
	Returns a structured JSON response with count, results, and a status message.
	"""
	# Get all query parameters from the URL
	title_term = request.args.get('title', '').lower()
	content_term = request.args.get('content', '').lower()

	# If no search terms are provided, return all posts
	if not title_term and not content_term:
		# Return all posts wrapped in the new structured format for consistency
		return jsonify({
			"count": len(POSTS),
			"results": POSTS,
			"message": f"{len(POSTS)} results found."
		})

	results = [
		post for post in POSTS
		if (title_term and title_term in post['title'].lower()) or
		   (content_term and content_term in post['content'].lower())
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
	return jsonify({
		"count": count,
		"results": results,
		"message": message
	})


if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5002, debug=True)