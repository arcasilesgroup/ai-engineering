# stills.tape — the README's terminal stills: real hook payloads through `ai-eng chain`, and the receipts they leave.
# Needs vhs, ttyd, ffmpeg, jq, cwebp and a built binary (`bun run build` writes dist/ai-eng). Regenerate, from this folder:
#   vhs stills.tape && for spec in deny-no-verify:215 deny-silence:215 rewrite-test:195 receipt:475; do cwebp -quiet -lossless -z 9 -crop 0 0 1080 ${spec##*:} ${spec%%:*}.png -o ../readme/${spec%%:*}.webp; done; rm -f *.png stills.webm
# The window is 520 px tall; each still is cropped to the lines its command printed.
Output stills.webm
Set Shell "bash"
Set FontFamily "JetBrainsMono Nerd Font"
Set FontSize 14
Set Width 1080
Set Height 520
Set Padding 30
Set TypingSpeed 12ms
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

Type "cat .demo/payload-bash-commit.json | ai-eng chain PreToolUse; echo exit $?"
Enter
Sleep 2s
Screenshot deny-no-verify.png
Sleep 500ms
Hide
Type "clear"
Enter
Show

Type "cat .demo/payload-edit-silence.json | ai-eng chain PreToolUse; echo exit $?"
Enter
Sleep 2s
Screenshot deny-silence.png
Sleep 500ms
Hide
Type "clear"
Enter
Show

Type "cat .demo/payload-bash-test.json | ai-eng chain PreToolUse | jq .updatedInput"
Enter
Sleep 2s
Screenshot rewrite-test.png
Sleep 500ms
Hide
Type "clear"
Enter
Show

Type "ls .ai-engineering/receipts && jq . .ai-engineering/receipts/$(ls .ai-engineering/receipts | head -1)"
Enter
Sleep 2s
Screenshot receipt.png
Sleep 500ms
