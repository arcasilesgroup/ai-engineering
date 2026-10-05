# quickstart.tape — install the governance, then ask the repo how it is doing.
# Regenerate: cd .github/assets/tapes && vhs quickstart.tape   (needs vhs, ttyd, ffmpeg)
Output ../quickstart.gif
Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 13
Set Width 1080
Set Height 680
Set Padding 30
Set TypingSpeed 25ms
Set Theme '{"name":"ai-eng","background":"#001E2B","foreground":"#E8EDEB","cursor":"#00ED64","selection":"#00684A","black":"#001E2B","red":"#FF6960","green":"#00ED64","yellow":"#FFC010","blue":"#0498EC","purple":"#B45AF2","cyan":"#71F6BA","white":"#E8EDEB","brightBlack":"#5C6C75","brightRed":"#FF6960","brightGreen":"#00ED64","brightYellow":"#FFC010","brightBlue":"#0498EC","brightPurple":"#B45AF2","brightCyan":"#71F6BA","brightWhite":"#FFFFFF"}'
Hide
Type "export PATH=$PWD/../../../dist:$PATH"
Enter
Type "export HOME=$(mktemp -d) AI_ENG_HOME=$(mktemp -d)"
Enter
Type "PS1='$ '"
Enter
Type "cd $(mktemp -d) && git init -q . && mkdir -p src && clear"
Enter
Show
Type "ai-eng init --surface claude-code --yes"
Enter
Sleep 6s
Type "clear"
Enter
Type "ai-eng doctor"
Enter
Sleep 9s
