# Example — Go HTTP handler

A typed POST endpoint backed by `net/http` + `chi`. Demonstrates:
context propagation, parameterised storage, structured errors, no
panic in library code.

```go
// internal/markets/handler.go
package markets

import (
	"encoding/json"
	"errors"
	"net/http"

	"github.com/go-chi/chi/v5"
)

type CreateMarketRequest struct {
	Symbol    string  `json:"symbol"`
	LastPrice float64 `json:"last_price"`
}

type Handler struct {
	repo Repository
}

func NewHandler(repo Repository) *Handler { return &Handler{repo: repo} }

func (h *Handler) Routes() http.Handler {
	r := chi.NewRouter()
	r.Post("/markets", h.create)
	return r
}

func (h *Handler) create(w http.ResponseWriter, r *http.Request) {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var req CreateMarketRequest
	if err := dec.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid_json"})
		return
	}
	if req.Symbol == "" || req.LastPrice <= 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid_payload"})
		return
	}
	if err := h.repo.Create(r.Context(), req); err != nil {
		if errors.Is(err, ErrSymbolTaken) {
			writeJSON(w, http.StatusConflict, map[string]string{"error": "symbol_taken"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal"})
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{"status": "created"})
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
```

## TDD pairing

```go
// internal/markets/handler_test.go
package markets

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

type fakeRepo struct{ created int }

func (f *fakeRepo) Create(ctx context.Context, req CreateMarketRequest) error {
	f.created++
	return nil
}

func TestCreate_RejectsEmptyBody(t *testing.T) {
	t.Parallel()
	h := NewHandler(&fakeRepo{})
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/markets", bytes.NewBufferString(``))
	h.Routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("got %d, want 400", rec.Code)
	}
}
```
