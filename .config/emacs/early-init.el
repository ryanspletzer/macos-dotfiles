;;; early-init.el --- Early initialization  -*- lexical-binding: t; -*-

;;; Commentary:
;; Runs before init.el and before the package system / UI are initialized.

;;; Code:

;; --- GC tuning -----------------------------------------------------------
;; Raise the GC threshold during init for faster startup, then lower it.
(setq gc-cons-threshold (* 128 1024 1024))  ; 128 MB during init
(add-hook 'emacs-startup-hook
          (lambda () (setq gc-cons-threshold (* 16 1024 1024))))  ; 16 MB after

;; --- UI suppression (before frame draws) ---------------------------------
(setq default-frame-alist
      '((width . 200)
        (height . 55)
        (tool-bar-lines . 0)
        (vertical-scroll-bars . nil)
        (menu-bar-lines . 0)))

(setq inhibit-startup-screen t
      inhibit-startup-message t
      inhibit-startup-echo-area-message user-login-name)

;; --- Package archives ----------------------------------------------------
(setq package-archives
      '(("gnu"    . "https://elpa.gnu.org/packages/")
        ("nongnu" . "https://elpa.nongnu.org/nongnu/")
        ("melpa"  . "https://melpa.org/packages/")))

;; --- Redirect custom.el out of init.el -----------------------------------
(setq custom-file (expand-file-name "custom.el" user-emacs-directory))

;;; early-init.el ends here
