# chain.tape — three real hook payloads through the guard dispatcher, and what comes back.
# Regenerate: cd .github/assets/tapes && vhs chain.tape   (needs vhs, ttyd, ffmpeg, jq)
Output ../chain.gif
Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 13
Set Width 1080
Set Height 420
Set Padding 30
Set TypingSpeed 22ms
Set Theme '{"name":"ai-eng","background":"#001E2B","foreground":"#E8EDEB","cursor":"#00ED64","selection":"#00684A","black":"#001E2B","red":"#FF6960","green":"#00ED64","yellow":"#FFC010","blue":"#0498EC","purple":"#B45AF2","cyan":"#71F6BA","white":"#E8EDEB","brightBlack":"#5C6C75","brightRed":"#FF6960","brightGreen":"#00ED64","brightYellow":"#FFC010","brightBlue":"#0498EC","brightPurple":"#B45AF2","brightCyan":"#71F6BA","brightWhite":"#FFFFFF"}'
Hide
Type "export PATH=$PWD/../../../dist:$PATH"
Enter
Type "export HOME=$(mktemp -d) AI_ENG_HOME=$(mktemp -d)"
Enter
Type "PS1='$ '"
Enter
Type "cd $(mktemp -d) && git init -q . && ai-eng init --surface claude-code --yes >/dev/null 2>&1 && cp -r $OLDPWD/demo .demo && clear"
Enter
Show
Type "cat .demo/payload-bash-commit.json | ai-eng chain PreToolUse | jq -c .permission"
Enter
Sleep 3s
Type "cat .demo/payload-edit-silence.json | ai-eng chain PreToolUse | jq -c .permission"
Enter
Sleep 3s
Type "cat .demo/payload-bash-test.json | ai-eng chain PreToolUse | jq -c .updatedInput"
Enter
Sleep 3s
Type "ls .ai-engineering/receipts/*.json | grep -vE 'summary|denies' | wc -l"
Enter
Sleep 2500ms
