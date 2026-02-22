;;; init.el --- Main configuration  -*- lexical-binding: t; -*-

;;; Commentary:
;; Vanilla Emacs 30+ config using built-ins where possible, MELPA otherwise.

;;; Code:

;; =========================================================================
;; 1. Package bootstrap
;; =========================================================================
(require 'use-package)
(setq use-package-always-ensure t)

;; Refresh archives on first launch (when elpa/ doesn't exist yet).
(unless (file-exists-p (expand-file-name "elpa" user-emacs-directory))
  (package-refresh-contents))

;; =========================================================================
;; 2. System / PATH
;; =========================================================================
;; Pull PATH from the login shell so Homebrew, pyenv, nvm, cargo, etc.
;; are available inside Emacs (especially GUI launches).
(use-package exec-path-from-shell
  :config
  (dolist (var '("PATH" "MANPATH" "GOPATH" "PYENV_ROOT" "NVM_DIR"
                 "CARGO_HOME" "GPG_TTY"))
    (add-to-list 'exec-path-from-shell-variables var))
  (exec-path-from-shell-initialize))

;; =========================================================================
;; 3. Core editor
;; =========================================================================
;; Encoding
(set-language-environment "UTF-8")
(prefer-coding-system 'utf-8)

;; Clipboard integration
(setq select-enable-clipboard t
      select-enable-primary t)

;; Line numbers (absolute)
(global-display-line-numbers-mode 1)

;; Auto-revert files changed on disk
(global-auto-revert-mode 1)
(setq global-auto-revert-non-file-buffers t)

;; Indentation defaults (2 spaces, no tabs)
(setq-default indent-tabs-mode nil
              tab-width 2)

;; Auto-close pairs
(electric-pair-mode 1)

;; Trim trailing whitespace on save
(add-hook 'before-save-hook #'delete-trailing-whitespace)

;; Ensure final newline
(setq require-final-newline t)

;; Backups in a single directory
(setq backup-directory-alist
      `(("." . ,(expand-file-name "backups" user-emacs-directory))))
(setq make-backup-files t
      backup-by-copying t
      delete-old-versions t
      kept-new-versions 6
      kept-old-versions 2
      version-control t)

;; Smoother scrolling
(setq scroll-conservatively 101
      scroll-margin 3)

;; Short yes/no prompts
(setq use-short-answers t)

;; =========================================================================
;; 4. UI / appearance
;; =========================================================================
;; Font (GUI only)
(when (display-graphic-p)
  (set-face-attribute 'default nil
                      :family "CaskaydiaCove Nerd Font"
                      :height 120))

;; Theme
(use-package doom-themes
  :config
  (load-theme 'doom-dark+ t)
  (doom-themes-org-config))

;; Modeline
(use-package doom-modeline
  :init (doom-modeline-mode 1)
  :config
  (setq doom-modeline-height 28
        doom-modeline-bar-width 4))

;; Icons for modeline (run M-x nerd-icons-install-fonts on first launch)
(use-package nerd-icons)

;; Column ruler
(setq-default display-fill-column-indicator-column 80)
(global-display-fill-column-indicator-mode 1)

;; Highlight current line
(global-hl-line-mode 1)

;; =========================================================================
;; 5. Completion (minibuffer)
;; =========================================================================
;; Vertical completion UI
(use-package vertico
  :init (vertico-mode 1))

;; Flexible matching
(use-package orderless
  :custom
  (completion-styles '(orderless basic))
  (completion-category-overrides '((file (styles basic partial-completion)))))

;; Rich annotations in minibuffer
(use-package marginalia
  :init (marginalia-mode 1))

;; Search and navigation commands
(use-package consult
  :bind (("C-x b"   . consult-buffer)
         ("C-x 4 b" . consult-buffer-other-window)
         ("M-g g"   . consult-goto-line)
         ("M-g M-g" . consult-goto-line)
         ("M-s l"   . consult-line)
         ("M-s r"   . consult-ripgrep)
         ("M-s f"   . consult-find)))

;; =========================================================================
;; 6. In-buffer completion
;; =========================================================================
(use-package corfu
  :custom
  (corfu-auto t)
  (corfu-auto-delay 0.2)
  (corfu-auto-prefix 2)
  :init (global-corfu-mode 1))

(use-package cape
  :init
  (add-hook 'completion-at-point-functions #'cape-dabbrev)
  (add-hook 'completion-at-point-functions #'cape-file)
  (add-hook 'completion-at-point-functions #'cape-keyword))

;; =========================================================================
;; 7. Snippets
;; =========================================================================
(use-package yasnippet
  :config (yas-global-mode 1))

(use-package yasnippet-snippets)

;; =========================================================================
;; 8. LSP (eglot — built-in)
;; =========================================================================
;; Server installation (do these externally):
;;   TypeScript:  npm i -g typescript-language-server typescript
;;   Go:          go install golang.org/x/tools/gopls@latest
;;   Python:      pip install python-lsp-server   (or pipx)
;;   Bash:        npm i -g bash-language-server
;;   YAML:        npm i -g yaml-language-server
;;   JSON:        npm i -g vscode-langservers-extracted
;;   Lua:         brew install lua-language-server
;;   Ruby:        gem install solargraph
;;   Rust:        rustup component add rust-analyzer
;;   C#:          dotnet tool install -g csharp-ls
;;   Dockerfile:  npm i -g dockerfile-language-server-nodejs
(use-package eglot
  :ensure nil  ; built-in
  :hook ((typescript-ts-mode . eglot-ensure)
         (tsx-ts-mode        . eglot-ensure)
         (js-ts-mode         . eglot-ensure)
         (go-ts-mode         . eglot-ensure)
         (python-ts-mode     . eglot-ensure)
         (bash-ts-mode       . eglot-ensure)
         (sh-mode            . eglot-ensure)
         (yaml-ts-mode       . eglot-ensure)
         (json-ts-mode       . eglot-ensure)
         (lua-ts-mode        . eglot-ensure)
         (ruby-ts-mode       . eglot-ensure)
         (rust-ts-mode       . eglot-ensure)
         (csharp-ts-mode     . eglot-ensure)
         (dockerfile-ts-mode . eglot-ensure)))

;; =========================================================================
;; 9. Tree-sitter
;; =========================================================================
;; Auto-install grammars and remap to tree-sitter modes.
;; Run M-x treesit-auto-install-all on first launch.
(use-package treesit-auto
  :custom (treesit-auto-install 'prompt)
  :config
  (treesit-auto-add-to-auto-mode-alist 'all)
  (global-treesit-auto-mode 1))

;; =========================================================================
;; 10. Syntax checking (flymake — built-in)
;; =========================================================================
(use-package flymake
  :ensure nil
  :hook (prog-mode . flymake-mode)
  :bind (:map flymake-mode-map
              ("M-n" . flymake-goto-next-error)
              ("M-p" . flymake-goto-prev-error)))

;; =========================================================================
;; 11. Git
;; =========================================================================
(use-package magit
  :bind ("C-x g" . magit-status)
  :config
  ;; Point to Homebrew GPG for commit signing.
  (setq magit-gpg-executable "/opt/homebrew/bin/gpg"))

;; =========================================================================
;; 12. File navigation
;; =========================================================================
;; Dired — show dotfiles
(setq dired-listing-switches "-alh")

;; project.el — add magit to project menu
(with-eval-after-load 'project
  (define-key project-prefix-map "m" #'magit-project-status)
  (add-to-list 'project-switch-commands '(magit-project-status "Magit") t))

;; =========================================================================
;; 13. Formatting (apheleia — async format-on-save)
;; =========================================================================
(use-package apheleia
  :config
  (apheleia-global-mode 1)
  ;; Disable for modes without a reliable formatter.
  (dolist (mode '(css-mode css-ts-mode scss-mode powershell-mode))
    (setf (alist-get mode apheleia-mode-alist) nil)))

;; =========================================================================
;; 14. Undo
;; =========================================================================
(use-package vundo
  :bind ("C-x u" . vundo))

;; =========================================================================
;; 15. Which-key (built-in in Emacs 30)
;; =========================================================================
(use-package which-key
  :ensure nil
  :config
  (setq which-key-idle-delay 0.5)
  (which-key-mode 1))

;; =========================================================================
;; 16. Language-specific
;; =========================================================================
;; Python — 4-space indent
(add-hook 'python-ts-mode-hook
          (lambda ()
            (setq-local tab-width 4
                        python-indent-offset 4)))

;; Go — tabs (go fmt default)
(add-hook 'go-ts-mode-hook
          (lambda ()
            (setq-local indent-tabs-mode t
                        tab-width 4)))

;; PowerShell — 4-space indent
(use-package powershell
  :mode ("\\.ps[dm]?1\\'" . powershell-mode)
  :hook (powershell-mode . (lambda ()
                             (setq-local tab-width 4
                                         indent-tabs-mode nil))))

;; Fish shell
(use-package fish-mode)

;; Dockerfile
(use-package dockerfile-mode)

;; Markdown — visual line wrapping
(add-hook 'markdown-mode-hook #'visual-line-mode)

;; Org — disable line numbers
(add-hook 'org-mode-hook (lambda () (display-line-numbers-mode -1)))

;; =========================================================================
;; 17. Keybindings / window management
;; =========================================================================
;; Shift+arrow for Emacs-internal window switching.
(windmove-default-keybindings)

;; ibuffer (better buffer list) at C-x C-b
(global-set-key (kbd "C-x C-b") #'ibuffer)

;; =========================================================================
;; 18. Finalization
;; =========================================================================
;; Load custom.el if it exists.
(when (file-exists-p custom-file)
  (load custom-file 'noerror 'nomessage))

;; Ensure Homebrew is on exec-path (belt-and-suspenders).
(add-to-list 'exec-path "/opt/homebrew/bin")

;; Startup timing
(add-hook 'emacs-startup-hook
          (lambda ()
            (message "Emacs ready in %.2f seconds with %d garbage collections."
                     (float-time (time-subtract after-init-time before-init-time))
                     gcs-done)))

;;; init.el ends here
