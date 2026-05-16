# Example — Go table-driven test

Demonstrates the canonical Go testing pattern: one test function with
many sub-tests, `t.Parallel()`, helper with `t.Helper()`, and
`-race`-clean state.

```go
// internal/markets/symbol.go
package markets

import (
	"errors"
	"strings"
	"unicode"
)

var ErrInvalidSymbol = errors.New("invalid symbol")

// NormalizeSymbol upper-cases the symbol and validates it is 1-10
// ASCII letters. Returns ErrInvalidSymbol on any other input.
func NormalizeSymbol(input string) (string, error) {
	trimmed := strings.TrimSpace(input)
	if l := len(trimmed); l == 0 || l > 10 {
		return "", ErrInvalidSymbol
	}
	for _, r := range trimmed {
		if !unicode.IsLetter(r) || r > unicode.MaxASCII {
			return "", ErrInvalidSymbol
		}
	}
	return strings.ToUpper(trimmed), nil
}
```

```go
// internal/markets/symbol_test.go
package markets

import (
	"errors"
	"testing"
)

func TestNormalizeSymbol(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    string
		wantErr error
	}{
		{"empty", "", "", ErrInvalidSymbol},
		{"too long", "ABCDEFGHIJK", "", ErrInvalidSymbol},
		{"non-letter", "BTC1", "", ErrInvalidSymbol},
		{"lowercase", "btc", "BTC", nil},
		{"trim", "  eth ", "ETH", nil},
	}

	for _, tt := range tests {
		tt := tt // capture
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := NormalizeSymbol(tt.input)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}
			if got != tt.want {
				t.Errorf("got = %q, want %q", got, tt.want)
			}
		})
	}
}
```
