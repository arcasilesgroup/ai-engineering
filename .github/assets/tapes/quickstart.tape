# quickstart.tape — govern a throwaway repo with the installed `ai-eng` CLI, then verify the chain.
# Re-runnable after any release:
#   ( cd .github/assets/tapes && vhs quickstart.tape )   # needs vhs, ttyd, ffmpeg, ai-eng on PATH
Output ../quickstart.gif

Set Shell "bash"
Set FontFamily "JetBrainsMono Nerd Font"
Set FontSize 15
Set LineHeight 1.12
Set Width 1180
Set Height 880
Set Padding 20
Set Margin 14
Set MarginFill "#112733"
Set BorderRadius 12
Set WindowBar Colorful
Set WindowBarSize 34
Set Framerate 24
Set TypingSpeed 26ms
Set Theme '{"name":"ai-eng","background":"#001E2B","foreground":"#E8EDEB","cursor":"#00ED64","selection":"#00684A","black":"#001E2B","red":"#FF6960","green":"#00ED64","yellow":"#FFC010","blue":"#0498EC","purple":"#B45AF2","cyan":"#71F6BA","white":"#E8EDEB","brightBlack":"#889397","brightRed":"#FF6960","brightGreen":"#00ED64","brightYellow":"#FFC010","brightBlue":"#0498EC","brightPurple":"#B45AF2","brightCyan":"#71F6BA","brightWhite":"#FFFFFF"}'

Hide
Type "unset AI_ENG_HOME GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM"
Enter
Type "export AI_ENG_NO_UPDATE_NOTICES=1"
Enter
Type "DEMO_ROOT=$(mktemp -d /tmp/aie-demo.XXXXXX) && export HOME=$DEMO_ROOT/home"
Enter
Type "mkdir -p $HOME $DEMO_ROOT/seed $DEMO_ROOT/my-app/src && git -C $DEMO_ROOT/seed init -q . && (cd $DEMO_ROOT/seed && ai-eng init --surface claude-code --yes >/dev/null 2>&1)"
Enter
Type "cd $DEMO_ROOT/my-app && git init -q ."
Enter
Type "PS1='\[\e[32m\]$\[\e[0m\] '"
Enter
Type "clear"
Enter
Sleep 400ms
Show

Sleep 300ms
Type "ai-eng init --surface claude-code --yes"
Enter
Sleep 3.0s

Hide
Type "clear"
Enter
Sleep 200ms
Show

Type "ai-eng doctor"
Enter
Sleep 4.2s

Hide
Type "rm -rf $DEMO_ROOT"
Enter
Sleep 200ms
