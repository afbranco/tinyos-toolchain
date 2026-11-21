# Normalizes the C that nesC generates (-fnesc-cfile), so that two builds can be compared:
#   awk -v tosroot="$TOSROOT" -f gen_c_norm.awk app.c
# - keeps only code that comes from TinyOS or the app: anything from /usr/ (glibc, gcc
#   headers) is dropped, as it changes with every apt update and is not TinyOS's code;
# - prints "@@ <source file>" when the source file changes ($TOSROOT shown as TOSROOT), so a
#   difference points at the file it comes from;
# - drops line markers and blank lines, and renames nesC's arg_0x<address> parameters (they
#   change from run to run) to arg_X, and the global __nesc_unnamed<N> counter (it depends on
#   how many unnamed types the system headers have) to __nesc_unnamedN.
/^# [0-9]+ "/ {
  f = $0
  sub(/^# [0-9]+ "/, "", f)
  sub(/".*$/, "", f)
  sys = (f ~ /^\/usr\//)
  if (!sys && f != shown) {
    s = f
    if (tosroot != "" && index(s, tosroot "/") == 1) s = "TOSROOT" substr(s, length(tosroot) + 1)
    print "@@ " s
    shown = f
  }
  next
}
/^#line / { next }
sys { next }
/^[ \t]*$/ { next }
{ gsub(/arg_0x[0-9a-f]+/, "arg_X"); gsub(/__nesc_unnamed[0-9]+/, "__nesc_unnamedN"); print }
