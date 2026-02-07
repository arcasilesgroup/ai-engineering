#!/usr/bin/env bash
# ai-engineering blocklist
# Additional blocked command patterns. User-customizable.
# This file is installed to .ai-engineering/hooks/blocklist.sh
# and sourced by pre-tool.sh.
#
# Add custom blocked patterns by adding functions below.
# Return exit code 2 to block, 0 to allow.

# Example custom block:
# check_custom_block() {
#   local input="$1"
#   if echo "$input" | grep -qE 'some-dangerous-command'; then
#     echo "BLOCKED: Custom rule — some-dangerous-command is not allowed."
#     return 2
#   fi
#   return 0
# }
