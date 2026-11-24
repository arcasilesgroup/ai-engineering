# quickstart-loop.tape — the README "Get it" demo as an endless loop whose whole cycle stays under 5 seconds.
# Why 5 s: WCAG 2.2.2 (Level A) lets motion that starts on its own and repeats run at most 5 s without a pause control, and GitHub markdown cannot host one.
# Loop: vhs writes the GIF89a NETSCAPE2.0 loop block with count 0 (repeat forever) by default; nothing strips it.
# Re-record after any release; tests/readme-assets.spec.ts reads the cycle length off the frame delays and fails at 5000 ms or more:
#   ( cd .github/assets/tapes && vhs quickstart-loop.tape ) && bun test tests/readme-assets.spec.ts
Output ../quickstart-loop.gif

Set Shell "bash"
Set FontFamily "JetBrainsMono Nerd Font"
Set FontSize 17
Set LineHeight 1.1
Set Width 1000
Set Height 700
Set Padding 14
Set Margin 10
Set MarginFill "#112733"
Set BorderRadius 12
Set WindowBar Colorful
Set WindowBarSize 32
Set Framerate 24
Set TypingSpeed 12ms
Set Theme '{"name":"ai-eng","background":"#001E2B","foreground":"#E8EDEB","cursor":"#00ED64","selection":"#00684A","black":"#001E2B","red":"#FF6960","green":"#00ED64","yellow":"#FFC010","blue":"#0498EC","purple":"#B45AF2","cyan":"#71F6BA","white":"#E8EDEB","brightBlack":"#C1C7C6","brightRed":"#FF6960","brightGreen":"#00ED64","brightYellow":"#FFC010","brightBlue":"#0498EC","brightPurple":"#B45AF2","brightCyan":"#71F6BA","brightWhite":"#FFFFFF"}'

# Hidden prep: a throwaway HOME whose machine-side canon is already installed, so the shown `init` is the repo step only.
Hide
Type "unset AI_ENG_HOME GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM"
Enter
Type "export AI_ENG_NO_UPDATE_NOTICES=1"
Enter
Type "DEMO_ROOT=$(mktemp -d /tmp/aie-demo.XXXXXX) && export HOME=$DEMO_ROOT/home"
Enter
Type "mkdir -p $HOME $DEMO_ROOT/seed $DEMO_ROOT/my-app && git -C $DEMO_ROOT/seed init -q . && (cd $DEMO_ROOT/seed && ai-eng init --surface claude-code --yes >/dev/null 2>&1)"
Enter
Type "cd $DEMO_ROOT/my-app && git init -q ."
Enter
Type "PS1='\[\e[32m\]$\[\e[0m\] '"
Enter
Type "clear"
Enter
Sleep 400ms
Show

# 1. init writes the contract.
Sleep 150ms
Type "ai-eng init --surface claude-code --yes"
Enter
Sleep 1300ms

# 2. the contract is on disk.
Hide
Type "clear"
Enter
Sleep 200ms
Show
Type "ls -A"
Enter
Sleep 700ms

# 3. doctor verifies the chain.
Hide
Type "clear"
Enter
Sleep 200ms
Show
Type "ai-eng doctor"
Enter
Sleep 1800ms

Hide
Type "rm -rf $DEMO_ROOT"
Enter
Sleep 200ms
