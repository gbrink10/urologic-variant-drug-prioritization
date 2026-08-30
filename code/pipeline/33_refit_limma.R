# Design-aware differential expression refit for the v29 revision.
#
# Replaces the elementary per-gene t-tests of v26-v28 with the standard
# Bioconductor treatment for each platform:
#
#   counts        edgeR filterByExpr + TMM + limma-voom
#   log2/linear   limma-trend (eBayes with trend=TRUE, robust=TRUE)
#   technical     duplicateCorrelation blocking on donor (penile SCC, where the
#   replicates    six "normal" arrays are three donors assayed twice)
#   paired        patient as a blocking factor (muscle-invasive bladder kinome)
#   batch         chip / batch as a covariate (sarcomatoid UC, small-cell)
#
# Inputs come from 32_prepare_matrices.py. Writes one standardized table per
# context to results/refit/DE_<CTX>.csv plus REFIT_SUMMARY.csv.

lib <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library", "4.6")
.libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages({library(limma); library(edgeR)})

args <- commandArgs(trailingOnly = TRUE)
repo <- if (length(args)) args[1] else getwd()
prep <- file.path(repo, "data", "prepared")
out  <- file.path(repo, "results", "refit")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

read_expr <- function(ctx) {
  m <- read.csv(file.path(prep, paste0(ctx, "_expr.csv")), row.names = 1,
                check.names = FALSE)
  as.matrix(m)
}
read_meta <- function(ctx) read.csv(file.path(prep, paste0(ctx, "_meta.csv")),
                                    check.names = FALSE, stringsAsFactors = FALSE)

summary_rows <- list()

record <- function(ctx, tt, method, design, contrast, extra = "") {
  tt$gene <- rownames(tt)
  tt <- tt[, c("gene", setdiff(names(tt), "gene"))]
  write.csv(tt, file.path(out, paste0("DE_", ctx, ".csv")), row.names = FALSE)
  n_sig <- sum(tt$adj.P.Val < 0.05, na.rm = TRUE)
  n_nom <- sum(tt$P.Value < 0.05, na.rm = TRUE)
  cat(sprintf("  %-16s %6d genes  %5d q<0.05  %6d p<0.05   %s\n",
              ctx, nrow(tt), n_sig, n_nom, method))
  summary_rows[[ctx]] <<- data.frame(
    context = ctx, genes = nrow(tt), n_q05 = n_sig, n_p05 = n_nom,
    method = method, design = design, contrast = contrast, notes = extra,
    stringsAsFactors = FALSE)
}

fit_counts <- function(ctx, design, coef, method_note) {
  E <- read_expr(ctx); M <- read_meta(ctx)
  d <- DGEList(counts = round(E))
  keep <- filterByExpr(d, design = design)
  d <- d[keep, , keep.lib.sizes = FALSE]
  d <- calcNormFactors(d, method = "TMM")
  v <- voom(d, design, plot = FALSE)
  fit <- eBayes(lmFit(v, design))
  tt <- topTable(fit, coef = coef, number = Inf, sort.by = "none")
  record(ctx, tt, method_note, paste(deparse(colnames(design)), collapse = ""),
         coef, sprintf("%d of %d genes passed filterByExpr", sum(keep), length(keep)))
}

fit_trend <- function(ctx, design, coef, E, method_note, block = NULL, extra = "") {
  # limma-trend needs a finite average-expression covariate for every row, so
  # drop non-finite rows and rows with no variance to fit on
  ok <- apply(E, 1, function(r) all(is.finite(r))) & (apply(E, 1, var) > 0)
  if (any(!ok)) {
    extra <- sprintf("%s; dropped %d non-finite/constant rows", extra, sum(!ok))
    E <- E[ok, , drop = FALSE]
  }
  fit <- if (is.null(block)) {
    lmFit(E, design)
  } else {
    dc <- duplicateCorrelation(E, design, block = block)
    extra <- sprintf("%s; duplicateCorrelation consensus %.3f", extra,
                     dc$consensus.correlation)
    lmFit(E, design, block = block, correlation = dc$consensus.correlation)
  }
  fit <- eBayes(fit, trend = TRUE, robust = TRUE)
  tt <- topTable(fit, coef = coef, number = Inf, sort.by = "none")
  record(ctx, tt, method_note, paste(colnames(design), collapse = " + "), coef, extra)
}

cat("REFIT (limma", as.character(packageVersion("limma")),
    "/ edgeR", as.character(packageVersion("edgeR")), ")\n")

## ---- count-based series -------------------------------------------------
M <- read_meta("ccRCC_METS")
des <- model.matrix(~ gender + metastatic, data = M)
colnames(des) <- make.names(colnames(des))
fit_counts("ccRCC_METS", des, grep("metastatic", colnames(des), value = TRUE)[1],
           "edgeR filterByExpr + TMM + voom + limma")

M <- read_meta("HLRCC")
M$group <- factor(M$group, levels = c("Normal", "Tumor"))
des <- model.matrix(~ group, data = M); colnames(des) <- make.names(colnames(des))
fit_counts("HLRCC", des, "groupTumor",
           "edgeR filterByExpr + TMM + voom + limma")

## ---- linear-scale RNA-seq summaries (RPKM / TPM) -------------------------
for (spec in list(
      list(ctx = "NEPC_CXCR7", form = ~ cell_line + treatment, coef = "treatmentshCXCR7"),
      list(ctx = "NEPC_DECITABINE", form = ~ treatment, coef = "treatmentdecitabine"),
      list(ctx = "NEPC_DNMT", form = ~ genotype, coef = "genotypeDNMT1KO"))) {
  E <- read_expr(spec$ctx); M <- read_meta(spec$ctx)
  keep <- rowSums(E > 1) >= max(2, ncol(E) / 3)
  E <- log2(E[keep, , drop = FALSE] + 1)
  if (spec$ctx == "NEPC_DNMT") M$genotype <- relevel(factor(M$genotype), "WT")
  if (spec$ctx == "NEPC_DECITABINE") M$treatment <- relevel(factor(M$treatment), "control")
  if (spec$ctx == "NEPC_CXCR7") M$treatment <- relevel(factor(M$treatment), "LKO")
  des <- model.matrix(spec$form, data = M); colnames(des) <- make.names(colnames(des))
  fit_trend(spec$ctx, des, spec$coef, E,
            "limma-trend on log2(TPM/RPKM+1), robust eBayes",
            extra = sprintf("%d of %d features passed expression filter",
                            sum(keep), length(keep)))
}

## ---- paired NanoString kinome -------------------------------------------
## No housekeeping probes on this panel, so the counts arrive background- and
## spike-in-corrected and are normalised here with TMM before voom.
M <- read_meta("MIBC_KINOME")
M$patient <- factor(M$patient); M$tissue_group <- relevel(factor(M$tissue_group), "normal")
des <- model.matrix(~ patient + tissue_group, data = M)
colnames(des) <- make.names(colnames(des))
fit_counts("MIBC_KINOME", des, "tissue_grouptumor",
           "TMM + voom, patient as blocking factor (matched pairs)")

## ---- penile SCC: technical replicates within normal donors --------------
E <- read_expr("PSCC"); M <- read_meta("PSCC")
M$group <- relevel(factor(M$group), "Normal")
des <- model.matrix(~ group, data = M); colnames(des) <- make.names(colnames(des))
fit_trend("PSCC", des, "groupTumor", E,
          "limma-trend with duplicateCorrelation on donor",
          block = factor(M$donor),
          extra = sprintf("%d normal arrays from %d donors",
                          sum(M$group == "Normal"),
                          length(unique(M$donor[M$group == "Normal"]))))

## ---- sarcomatoid vs conventional urothelial, chip as batch --------------
E <- read_expr("SarcUC"); M <- read_meta("SarcUC")
M$group <- relevel(factor(M$group), "UC"); M$chip <- factor(M$chip)
## Chip and group are COMPLETELY confounded in this series: all 28 sarcomatoid
## samples were hybridised on 4 chips and all 84 conventional samples on 15
## different chips, with no chip carrying both. ~ chip + group is therefore not
## estimable and no batch adjustment is possible. The contrast is fitted without
## it, and the confounding is recorded so the manuscript can state it.
tab <- table(M$chip, M$group)
mixed <- sum(rowSums(tab > 0) > 1)
des <- model.matrix(~ group, data = M); colnames(des) <- make.names(colnames(des))
fit_trend("SarcUC", des, "groupSARC", E,
          "limma-trend, group only - chip not estimable",
          extra = sprintf(paste("CONFOUNDED: %d chips, %d carry both groups;",
                                "batch effect cannot be separated from the",
                                "sarcomatoid/conventional contrast"),
                          nlevels(M$chip), mixed))

## ---- small-cell bladder cancer: one contrast per lineage subtype --------
E <- read_expr("SCBC"); M <- read_meta("SCBC")
M$batch <- factor(M$batch); M$subtype <- factor(M$subtype)
des <- model.matrix(~ 0 + subtype + batch, data = M)
colnames(des) <- make.names(colnames(des))
fit <- lmFit(E, des)
subs <- levels(M$subtype)
for (s in subs) {
  others <- setdiff(subs, s)
  cm <- makeContrasts(
    contrasts = paste0("subtype", s, " - (",
                       paste0("subtype", others, collapse = " + "), ")/",
                       length(others)),
    levels = des)
  f2 <- eBayes(contrasts.fit(fit, cm), trend = TRUE, robust = TRUE)
  tt <- topTable(f2, number = Inf, sort.by = "none")
  record(paste0("SCBC_", s), tt,
         "limma-trend, batch-adjusted, subtype vs mean of remaining subtypes",
         paste(colnames(des), collapse = " + "), paste(s, "vs rest"),
         sprintf("n=%d of %d", sum(M$subtype == s), nrow(M)))
}

sm <- do.call(rbind, summary_rows)
write.csv(sm, file.path(out, "REFIT_SUMMARY.csv"), row.names = FALSE)
cat("\nwrote", nrow(sm), "tables to", out, "\n")
