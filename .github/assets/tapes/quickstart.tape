# quickstart.tape — real terminal session of ai-eng 3.3.1 in a throwaway repository.
# Captures four real commands at human typing pace:
#   1. ai-eng init --surface claude-code --yes
#   2. ai-eng doctor (including live adversarial git commit -n -> DENY + Chain verified.)
#   3. ai-eng work (live lane board against base main)
#   4. ai-eng config --add cursor (second enforced surface + mirror verification)
#
# Run via the deterministic render script beside this tape so the raw recording is edited
# with the brand's intro card, burned-in captions, non-colour-only highlights, and closing card:
#   bash .github/assets/tapes/quickstart-video.sh
#
# Why this video has no 5-second ceiling: WCAG 2.2.2 governs motion that starts on its own.
# The README embeds a static poster image linking to .github/assets/quickstart.mp4, so nothing
# autoplays.

Output raw.mp4
Output raw.ascii

Set Shell "bash"
Set FontFamily "JetBrainsMono Nerd Font"
Set FontSize 15
Set LineHeight 1.12
Set Width 1732
Set Height 776
Set Padding 14
Set Margin 0
Set BorderRadius 0
Set Framerate 25
Set TypingSpeed 50ms
Set Theme '{"name":"ai-eng","background":"#001E2B","foreground":"#E8EDEB","cursor":"#00ED64","selection":"#00684A","black":"#001E2B","red":"#FF6960","green":"#00ED64","yellow":"#FFC010","blue":"#0498EC","purple":"#B45AF2","cyan":"#71F6BA","white":"#E8EDEB","brightBlack":"#C1C7C6","brightRed":"#FF6960","brightGreen":"#00ED64","brightYellow":"#FFC010","brightBlue":"#0498EC","brightPurple":"#B45AF2","brightCyan":"#71F6BA","brightWhite":"#FFFFFF"}'

# Hidden prep: throwaway HOME with global canon already installed (so init shows the repo step),
# plus a throwaway repository with local bare origin (main) and a feature branch (feat/auth).
Hide
Type@1ms "unset AI_ENG_HOME GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM"
Enter
Type@1ms "export AI_ENG_NO_UPDATE_NOTICES=1"
Enter
Type@1ms "DEMO_ROOT=$(mktemp -d /tmp/aie-demo.XXXXXX) && export HOME=$DEMO_ROOT/home"
Enter
Type@1ms "mkdir -p $HOME $DEMO_ROOT/seed $DEMO_ROOT/my-app"
Enter
Type@1ms "git -C $DEMO_ROOT/seed init -q -b main . && (cd $DEMO_ROOT/seed && ai-eng init --surface claude-code --yes >/dev/null 2>&1)"
Enter
Type@1ms "git init --bare -q -b main $DEMO_ROOT/origin.git"
Enter
Type@1ms "cd $DEMO_ROOT/my-app && git init -q -b main . && git config user.name 'demo' && git config user.email 'demo@example.com'"
Enter
Type@1ms "printf '# my-app\n' > README.md && git add README.md && git commit -q -m 'init' && git remote add origin $DEMO_ROOT/origin.git && git push -q -u origin main && git checkout -q -b feat/auth"
Enter
Type@1ms "PS1='\[\e[32m\]$\[\e[0m\] '"
Enter
Type@1ms "clear"
Enter
Sleep 600ms
Show

# Act 1: govern the repository for Claude Code.
Sleep 500ms
Type "ai-eng init --surface claude-code --yes"
Sleep 300ms
Enter
Sleep 2800ms

# Act 2: audit all checks, fire the live adversarial deny probe, and verify the chain.
Hide
Type@1ms "clear"
Enter
Sleep 250ms
Show
Sleep 500ms
Type "ai-eng doctor"
Sleep 300ms
Enter
Sleep 3000ms

# Act 3: inspect the live git lane board.
Hide
Type@1ms "clear"
Enter
Sleep 250ms
Show
Sleep 500ms
Type "ai-eng work"
Sleep 300ms
Enter
Sleep 2600ms

# Act 4: add Cursor as a second enforced surface.
Hide
Type@1ms "clear"
Enter
Sleep 250ms
Show
Sleep 500ms
Type "ai-eng config --add cursor"
Sleep 300ms
Enter
Sleep 2800ms

# Hidden cleanup of the throwaway workspace.
Hide
Type@1ms "rm -rf $DEMO_ROOT"
Enter
Sleep 200ms
