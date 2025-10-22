from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Allows cross-origin access

# Path to the JSON file (used for persistent storage in a later step)
JSON_FILE = 'posts.json'

# Temporary in-memory list for the current test
# We will replace this with loading from the JSON file in the next step
POSTS = [
	{"id": 1, "title": "First post", "content": "This is the first post."},
	{"id": 2, "title": "Second post", "content": "This is the second post."},
]

# Helper function to generate a new ID
def get_new_id(posts):
	"""Returns the next available unique ID."""
	# Returns the highest existing ID + 1, or 1 if the list is empty
	return max(post['id'] for post in posts) + 1 if posts else 1

# --- GET ENDPOINT (Existing) ---
@app.route('/api/posts', methods=['GET'])
def get_posts():
	"""Returns all blog posts."""
	return jsonify(POSTS)

# --- POST ENDPOINT (New: Creates a new post) ---
@app.route('/api/posts', methods=['POST'])
def add_post():
	"""Creates a new blog post from JSON data."""
	# 1. Retrieve JSON data from the request
	data = request.get_json()

	# 2. Error Handling: Check if 'title' and 'content' are provided
	if not data or 'title' not in data or 'content' not in data:
		return jsonify({
			"error": "Missing required fields",
			"required": ["title", "content"]
		}), 400  # HTTP 400 Bad Request

	# 3. Generate ID and create the new post object
	new_id = get_new_id(POSTS)

	new_post = {
		"id": new_id,
		"title": data['title'],
		"content": data['content']
	}

	# 4. Add the post to the list
	POSTS.append(new_post)

	# 5. Return successful response
	# HTTP 201 Created status code and the created object
	return jsonify(new_post), 201

# --- DELETE ENDPOINT (Existing) ---
@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
	"""Deletes a post by its ID from the in-memory list."""
	global POSTS

	# Find the post to be deleted
	post_to_delete = None
	for post in POSTS:
		if post['id'] == id:
			post_to_delete = post
			break

	# 404 Error Handling: If post is not found
	if post_to_delete is None:
		return jsonify({"error": f"Post with id {id} not found."}), 404

	# Delete the post from the list
	POSTS.remove(post_to_delete)

	# Return successful response (200 OK)
	return jsonify({
		"message": f"Post with id {id} has been deleted successfully."
	}), 200

# --- PUT ENDPOINT (New: Updates an existing post) ---
@app.route('/api/posts/<int:id>', methods=['PUT'])
def update_post(id):
	"""Updates an existing post by its ID with optional title/content changes."""
	global POSTS

	# 1. Find the post's index to allow direct modification
	post_index = -1
	for i, post in enumerate(POSTS):
		if post['id'] == id:
			post_index = i
			break

	# 2. 404 Error Handling: If post is not found
	if post_index == -1:
		return jsonify({"error": f"Post with id {id} not found."}), 404

	# 3. Retrieve JSON data and update the post
	data = request.get_json()
	post_to_update = POSTS[post_index]

	# Both fields are optional: only update if present in the JSON body
	if data:
		if 'title' in data:
			post_to_update['title'] = data['title']
		if 'content' in data:
			post_to_update['content'] = data['content']

	# 4. Return successful response (200 OK)
	# Return the fully updated post object
	return jsonify(post_to_update), 200


if __name__ == '__main__':
	# Starts the app on 0.0.0.0 so it is accessible via Codio
	app.run(host="0.0.0.0", port=5002, debug=True)
