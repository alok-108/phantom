;;; phantom-mode.el --- Major mode for the Phantom instruction layer -*- lexical-binding: t; -*-
;;
;; Phantom keeps ordinary Python as the host language and puts a typed
;; instruction layer in comments, for example:
;;
;;     #: phantom:0.1.0 meta.author("Payments team")
;;     #:ws:begin ... #:ws:end    (whitespace encoding)
;;     #:zw:begin ... #:zw:end    (zero-width encoding)
;;     #:phantom:hybrid           (hybrid-mode header)
;;
;; Install: copy this file to a directory on `load-path' and add
;;   (add-to-list 'auto-mode-alist '("\\.py\\'" . phantom-mode))
;;   (autoload 'phantom-mode "phantom-mode" nil t)
;; See docs/INSTALLATION.md ("Editor Support") for details.

(require 'python)

(defvar phantom-mode-instructions
  '("event.declare" "event.on" "diagnostic.note" "diagnostic.warn"
    "counter.create" "counter.increment" "counter.decrement" "counter.reset"
    "meta.author" "meta.version" "meta.license" "meta.tags")
  "Phantom instruction keywords highlighted by `phantom-mode'.")

(defvar phantom-mode-markers
  '("#:ws:begin" "#:ws:end" "#:zw:begin" "#:zw:end" "#:phantom:hybrid")
  "Phantom encoding block markers highlighted by `phantom-mode'.")

(defvar phantom-mode-font-lock-keywords
  `((,(concat "^[ \t]*#: *phantom:[0-9]+\\.[0-9]+\\.[0-9]+")
     . font-lock-keyword-face)
    (,(regexp-opt phantom-mode-instructions 'words)
     . font-lock-function-name-face)
    (,(regexp-opt phantom-mode-markers)
     . font-lock-constant-face))
  "Font-lock keywords for `phantom-mode'.")

;;;###autoload
(define-derived-mode phantom-mode python-mode "Phantom"
  "Major mode for Phantom dual-layer Python files.
Derived from `python-mode', with extra highlighting for the Phantom
instruction layer: the `#: phantom:<semver>' prefix, instruction
keywords, and encoding block markers."
  (setq-local font-lock-defaults
              '(phantom-mode-font-lock-keywords nil nil nil nil)))

(provide 'phantom-mode)
;;; phantom-mode.el ends here
