from flask import jsonify, Flask
from ..utils.exceptions import (
    K8sVisualizerError,
    K8sConnectionError,
    ResourceNotFoundError,
    InvalidResourceTypeError
)
from ..utils.logger import logger

def register_error_handlers(app: Flask):
    @app.errorhandler(K8sConnectionError)
    def handle_k8s_connection_error(error):
        logger.error(f"Kubernetes connection error: {str(error)}")
        return jsonify({"error": "Failed to connect to Kubernetes cluster"}), 503

    @app.errorhandler(ResourceNotFoundError)
    def handle_resource_not_found(error):
        logger.warning(f"Resource not found: {str(error)}")
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(InvalidResourceTypeError)
    def handle_invalid_resource_type(error):
        logger.warning(f"Invalid resource type: {str(error)}")
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500