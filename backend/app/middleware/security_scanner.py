"""
Dual security scanning middleware.
Intercepts AI-related API requests and scans both input and output
through Hidden Layer and AIM in parallel.
"""


# Note: Security scanning is done at the service/endpoint level rather than
# as HTTP middleware, because we need granular control over what gets scanned
# (agent reasoning steps, tool calls, etc.) and the ability to log context
# about which feature triggered the scan.
#
# The dual_security_scan() function in security_service.py is called directly
# by each endpoint/service that involves AI operations.
#
# This file is kept as a placeholder for any future HTTP-level middleware needs
# (e.g., rate limiting, request logging).
