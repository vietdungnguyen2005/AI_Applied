# P00 source evidence index

Project2 baseline: `32d82862526754b46efb774327ccc4774a4decf7`. These are source observations, not runtime results.

## app/api/auth/[action]/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/auth/[action]/route.ts)

```text
5: async function forward(request: Request, context: Context) {
15: export const GET = forward;
16: export const POST = forward;
```

## app/api/cart/quantity/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/cart/quantity/route.ts)

```text
11: export async function POST(request: Request) {
```

## app/api/catalog/products/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/catalog/products/route.ts)

```text
3: export async function GET(request: Request) {
```

## app/api/ops/imports/[jobId]/inspection/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/imports/[jobId]/inspection/route.ts)

```text
3: export async function GET(request: Request, context: {params:Promise<{jobId:string}>}) {
```

## app/api/ops/imports/[jobId]/restart/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/imports/[jobId]/restart/route.ts)

```text
3: export async function POST(request: Request, context: { params: Promise<{ jobId: string }> }) {
```

## app/api/ops/imports/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/imports/route.ts)

```text
3: export async function GET(request: Request) {
7: export async function POST(request: Request) {
```

## app/api/ops/integration-profiles/[profileId]/[version]/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/integration-profiles/[profileId]/[version]/route.ts)

```text
3: export async function PATCH(request: Request, context: {params:Promise<{profileId:string;version:string}>}) {
```

## app/api/ops/integration-profiles/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/integration-profiles/route.ts)

```text
3: export async function GET(request: Request) {
6: export async function POST(request: Request) {
```

## app/api/ops/inventory/snapshot/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/inventory/snapshot/route.ts)

```text
3: export async function GET(request: Request) {
```

## app/api/ops/onboarding/[profileId]/[version]/[action]/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/onboarding/[profileId]/[version]/[action]/route.ts)

```text
3: export async function POST(request: Request, context: {params:Promise<{profileId:string;version:string;action:string}>}) {
```

## app/api/ops/orders/[orderNumber]/fulfillment/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/orders/[orderNumber]/fulfillment/route.ts)

```text
3: export const runtime = "nodejs";
7: export async function PATCH(request: Request, context: RouteContext): Promise<Response> {
```

## app/api/ops/orders/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/orders/route.ts)

```text
3: export const runtime = "nodejs";
5: export async function GET(request: Request): Promise<Response> {
```

## app/api/ops/reconciliations/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/ops/reconciliations/route.ts)

```text
3: export async function GET(request: Request) {
7: export async function POST(request: Request) {
```

## app/api/orders/[orderNumber]/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/orders/[orderNumber]/route.ts)

```text
3: export async function GET(
```

## app/api/orders/checkout/cancel/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/orders/checkout/cancel/route.ts)

```text
3: export async function POST(request: Request) {
```

## app/api/orders/checkout/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/orders/checkout/route.ts)

```text
3: export async function GET(request: Request) {
```

## app/api/orders/route.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/app/api/orders/route.ts)

```text
3: export async function POST(request: Request) {
```

## backend/src/main/java/dev/vmarket/catalog/CatalogController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/catalog/CatalogController.java)

```text
9: @RequestMapping("/api/catalog")
13:     public CatalogController(CatalogQueryService catalog) {
17:     @GetMapping("/products")
```

## backend/src/main/java/dev/vmarket/migration/ImportChunkService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/ImportChunkService.java)

```text
21:     public ImportChunkService(
30:     public int applyNextChunk(ImportWorkClaim claim) {
34:         String mode = jdbc.sql("SELECT import_mode FROM migration_job WHERE id=:id FOR UPDATE")
43:                 ORDER BY external_sku, row_number LIMIT :limit FOR UPDATE
107:                         INSERT INTO inventory_movement(id,product_id,movement_type,quantity_delta,reason,reference_id)
143:                 WHERE p.sku=:sku FOR UPDATE OF p,s
167:             public void afterCommit() {
187:     private record ImportRow(
197:     private record ProductState(
```

## backend/src/main/java/dev/vmarket/migration/ImportRecoveryService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/ImportRecoveryService.java)

```text
19:     private static final int MAX_RECOVERIES = 3;
25:     public ImportRecoveryService(
38:     public boolean recoverOne() {
46:                     ORDER BY j.updated_at,j.id LIMIT 1 FOR UPDATE OF j SKIP LOCKED
53:                       AND state='CLAIMED' AND dispatch_requested=TRUE AND lease_until<=clock_timestamp() FOR UPDATE
67:             if (owner.recoveryCount() >= MAX_RECOVERIES) {
144:     private record Ownership(long generation, int recoveryCount) {}
```

## backend/src/main/java/dev/vmarket/migration/ImportRepositoryFence.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/ImportRepositoryFence.java)

```text
19:     public static JobRepository wrap(
52:                             jdbc.sql("SELECT id FROM migration_job WHERE id=:job FOR UPDATE")
```

## backend/src/main/java/dev/vmarket/migration/IntegrationProfileController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/IntegrationProfileController.java)

```text
14: @RequestMapping("/api/ops/integration-profiles")
19:     public IntegrationProfileController(IntegrationProfileService profiles, OpsAuthorizer authorizer) {
24:     @GetMapping
25:     List<IntegrationProfileService.Profile> recent(@RequestHeader("X-V-Market-Ops-Secret") String secret) {
26:         authorizer.authorize(secret);
30:     @PostMapping
32:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
35:         authorizer.authorize(secret);
39:     public record Activation(boolean active) {}
41:     @PatchMapping("/{profileId}/{version}")
43:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
48:         authorizer.authorize(secret);
```

## backend/src/main/java/dev/vmarket/migration/IntegrationProfileService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/IntegrationProfileService.java)

```text
17:     public IntegrationProfileService(JdbcClient jdbc, ObjectMapper json) {
22:     public record Profile(
35:         public List<String> requiredFields() {
36:             return List.of("sku", "name", "on_hand");
40:         public Map<String, String> normalization() {
45:         public Map<String, ?> validation() {
48:                     Map.of("type", "string", "minLength", 1, "maxLength", 64),
50:                     Map.of("type", "string", "minLength", 1, "maxLength", 160),
52:                     Map.of("type", "integer", "min", 0, "max", 1_000_000));
56:     public record Definition(
66:     public Profile find(String id, int version, boolean lock) {
67:         return jdbc.sql(SELECT + " WHERE profile_id=:id AND version=:version" + (lock ? " FOR UPDATE" : ""))
75:     public Profile requireActive(String id, int version, boolean lock) {
84:     public Profile publish(Definition d, String actor) {
91:                 || !d.mapping().keySet().equals(java.util.Set.of("sku", "name", "on_hand"))
108:                 INSERT INTO integration_profile(profile_id,version,encoding,vendor_code,mapping,sku_normalization,created_by,updated_by)
126:     public Profile activate(String id, int version, boolean active, String actor) {
143:                 INSERT INTO audit_event(id,actor,action,aggregate_type,aggregate_id,details)
162:     public List<Profile> recent() {
163:         return jdbc.sql(SELECT + " ORDER BY profile_id,version DESC LIMIT 100")
```

## backend/src/main/java/dev/vmarket/migration/InventorySnapshotController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/InventorySnapshotController.java)

```text
18:     public InventorySnapshotController(JdbcClient jdbc, OpsAuthorizer authorizer) {
23:     @GetMapping(value = "/api/ops/inventory/snapshot", produces = "text/csv;charset=UTF-8")
24:     ResponseEntity<String> export(@RequestHeader("X-V-Market-Ops-Secret") String secret) throws IOException {
25:         authorizer.authorize(secret);
56:     private record SnapshotRow(
```

## backend/src/main/java/dev/vmarket/migration/LegacyImportService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/LegacyImportService.java)

```text
28:     private static final int MAX_DATA_ROWS = 1000;
30:             List.of("sku", "vendor_code", "name", "on_hand", "price_minor");
38:     public LegacyImportService(
51:     public MigrationSummary importCsv(String sourceName, String encodingName, byte[] bytes) {
55:     public MigrationSummary importCsv(String sourceName, String encodingName, byte[] bytes, boolean asynchronous) {
59:         if (bytes == null || bytes.length == 0 || bytes.length > dev.vmarket.shared.RequestBodyLimits.CSV_MAX_BYTES) {
64:         String checksum = sha256(bytes);
75:         return findByChecksum(sha256(bytes), supportedCharset(encoding), profileId, profileVersion);
92:             jdbc.sql("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))")
125:     public MigrationSummary restart(UUID jobId) {
129:     public MigrationSummary restart(UUID jobId, boolean asynchronous) {
133:                 String state = jdbc.sql("SELECT status FROM migration_job WHERE id=:id FOR UPDATE NOWAIT")
172:     public MigrationSummary find(UUID jobId) {
184:     public List<MigrationSummary> recent() {
188:                         FROM migration_job ORDER BY created_at DESC LIMIT 20
192:     public record Inspection(
200:     public Inspection inspect(UUID jobId) {
211:                                         "SELECT row_number,validation_error FROM staged_import_row WHERE job_id=:job AND valid=FALSE ORDER BY row_number LIMIT 1000")
246:                         INSERT INTO migration_job (
261:         jdbc.sql("INSERT INTO import_work_item(job_id) VALUES(:job)")
267:                             INSERT INTO staged_import_row (
324:             parser.forEach(record -> {
325:                 if (rows.size() >= MAX_DATA_ROWS)
326:                     throw new InvalidImportException("CSV input must contain at most " + MAX_DATA_ROWS + " data rows.");
417:     static String sha256(byte[] bytes) {
425:     record StagedRow(
```

## backend/src/main/java/dev/vmarket/migration/MigrationController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/MigrationController.java)

```text
16: @RequestMapping("/api/ops/imports")
21:     public MigrationController(LegacyImportService imports, OpsAuthorizer authorizer) {
26:     @PostMapping(consumes = "text/csv")
28:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
33:         authorizer.authorize(secret);
49:     @GetMapping
50:     List<MigrationSummary> recent(@RequestHeader("X-V-Market-Ops-Secret") String secret) {
51:         authorizer.authorize(secret);
55:     @PostMapping("/{jobId}/restart")
57:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
60:         authorizer.authorize(secret);
71:     @GetMapping("/{jobId}")
72:     MigrationSummary find(@RequestHeader("X-V-Market-Ops-Secret") String secret, @PathVariable UUID jobId) {
73:         authorizer.authorize(secret);
77:     @GetMapping("/{jobId}/inspection")
79:             @RequestHeader("X-V-Market-Ops-Secret") String secret, @PathVariable UUID jobId) {
80:         authorizer.authorize(secret);
```

## backend/src/main/java/dev/vmarket/migration/MigrationModels.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/MigrationModels.java)

```text
6: record MigrationSummary(
```

## backend/src/main/java/dev/vmarket/migration/OpsAuthorizer.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/OpsAuthorizer.java)

```text
10:     private final byte[] expectedSecret;
12:     public OpsAuthorizer(@Value("${vmarket.ops-secret}") String expectedSecret) {
13:         this.expectedSecret = expectedSecret.getBytes(StandardCharsets.UTF_8);
16:     public void authorize(String provided) {
17:         if (provided == null || !MessageDigest.isEqual(expectedSecret, provided.getBytes(StandardCharsets.UTF_8))) {
```

## backend/src/main/java/dev/vmarket/migration/SupplierOnboardingController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/SupplierOnboardingController.java)

```text
11: @RequestMapping("/api/ops/onboarding/{profileId}/{version}")
16:     public SupplierOnboardingController(SupplierOnboardingService onboarding, OpsAuthorizer authorizer) {
21:     @PostMapping(value = "/preview", consumes = "text/csv")
23:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
28:         authorizer.authorize(secret);
32:     @PostMapping(value = "/confirm", consumes = "text/csv")
34:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
41:         authorizer.authorize(secret);
```

## backend/src/main/java/dev/vmarket/migration/SupplierOnboardingService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/migration/SupplierOnboardingService.java)

```text
26:     public SupplierOnboardingService(
30:             @org.springframework.beans.factory.annotation.Value("${vmarket.ops-secret}") String secret) {
34:         this.receiptKey = secret.getBytes(StandardCharsets.UTF_8);
37:     public record RowError(int rowNumber, String reason) {}
39:     public record Sample(int rowNumber, String sku, String name, Integer onHand) {}
41:     public record Preview(
52:     record Prepared(byte[] canonical, List<LegacyImportService.StagedRow> rows) {}
55:             readOnly = true,
58:     public Preview preview(String id, int version, byte[] bytes, String actor) {
71:         String payload = (java.time.Instant.now().getEpochSecond() + 600) + ":" + LegacyImportService.sha256(bytes)
72:                 + ":" + LegacyImportService.sha256(prepared.canonical());
85:     public MigrationSummary confirm(
93:         if (!receipt.split(":")[2].equals(LegacyImportService.sha256(prepared.canonical())))
100:                 LegacyImportService.sha256(bytes),
110:         if (bytes == null || bytes.length == 0 || bytes.length > dev.vmarket.shared.RequestBodyLimits.CSV_MAX_BYTES)
114:         String[] fields = receipt.split(":");
118:                 || expires > java.time.Instant.now().getEpochSecond() + 600
119:                 || !fields[1].equals(LegacyImportService.sha256(bytes))
129:             var mac = javax.crypto.Mac.getInstance("HmacSHA256");
130:             mac.init(new javax.crypto.spec.SecretKeySpec(receiptKey, "HmacSHA256"));
133:                                     + LegacyImportService.sha256(actor.getBytes(StandardCharsets.UTF_8)) + ":"
142:         if (bytes == null || bytes.length == 0 || bytes.length > dev.vmarket.shared.RequestBodyLimits.CSV_MAX_BYTES)
166:             for (var record : parser) {
220:                     if (quantity < 0 || quantity > 1_000_000)
263:     private record SourceRow(int row, String sku, String name, String stock) {}
265:     private record Canonical(
```

## backend/src/main/java/dev/vmarket/ops/OpsOrderController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/ops/OpsOrderController.java)

```text
15: @RequestMapping("/api/ops/orders")
20:     public OpsOrderController(OpsOrderService orders, OpsAuthorizer authorizer) {
25:     @GetMapping
26:     List<OpsOrder> recent(@RequestHeader("X-V-Market-Ops-Secret") String secret) {
27:         authorizer.authorize(secret);
31:     @PatchMapping("/{orderNumber}/fulfillment")
33:             @RequestHeader("X-V-Market-Ops-Secret") String secret,
36:         authorizer.authorize(secret);
```

## backend/src/main/java/dev/vmarket/order/OrderController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/order/OrderController.java)

```text
16: @RequestMapping("/api/orders")
21:     public OrderController(OrderService orders, OrderTrackingService tracking) {
26:     @PostMapping
35:     @GetMapping("/{orderNumber}")
40:     @PostMapping("/checkout/cancel")
53:     @GetMapping("/checkout")
```

## backend/src/main/java/dev/vmarket/reconciliation/ReconciliationController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/reconciliation/ReconciliationController.java)

```text
16: @RequestMapping("/api/ops/reconciliations")
21:     public ReconciliationController(ReconciliationService reconciliations, OpsAuthorizer authorizer) {
26:     @PostMapping
29:             @RequestHeader("X-V-Market-Ops-Secret") String secret, @Valid @RequestBody ReconciliationRequest request) {
30:         authorizer.authorize(secret);
34:     @GetMapping
35:     List<ReconciliationReport> recent(@RequestHeader("X-V-Market-Ops-Secret") String secret) {
36:         authorizer.authorize(secret);
```

## backend/src/main/java/dev/vmarket/reconciliation/ReconciliationModels.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/reconciliation/ReconciliationModels.java)

```text
8: record ReconciliationRequest(@NotNull UUID migrationJobId) {}
10: record ReconciliationReport(
20: record Discrepancy(
```

## backend/src/main/java/dev/vmarket/reconciliation/ReconciliationService.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/reconciliation/ReconciliationService.java)

```text
17:     public ReconciliationService(JdbcClient jdbc, MeterRegistry metrics) {
23:     public ReconciliationReport reconcile(UUID migrationJobId) {
35:                         INSERT INTO reconciliation_run (id, migration_job_id, status, created_at)
128:     @Transactional(readOnly = true)
129:     public List<ReconciliationReport> recent() {
132:                         FROM reconciliation_run ORDER BY created_at DESC LIMIT 20
159:                         INSERT INTO reconciliation_discrepancy (
173:     private record SourceState(
```

## backend/src/main/java/dev/vmarket/shared/BffAuthenticationFilter.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/shared/BffAuthenticationFilter.java)

```text
18:     private final byte[] expectedSecret;
20:     public BffAuthenticationFilter(@Value("${vmarket.bff-secret}") String expectedSecret) {
21:         this.expectedSecret = expectedSecret.getBytes(StandardCharsets.UTF_8);
34:         String provided = request.getHeader("X-V-Market-BFF-Secret");
35:         if (provided == null || !MessageDigest.isEqual(expectedSecret, provided.getBytes(StandardCharsets.UTF_8))) {
```

## backend/src/main/java/dev/vmarket/shared/OperatorSessionController.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/shared/OperatorSessionController.java)

```text
7: import org.springframework.security.web.csrf.CsrfToken;
13:     @GetMapping("/api/auth/session")
15:         CsrfToken csrf = (CsrfToken) request.getAttribute(CsrfToken.class.getName());
30:                 "csrfToken",
31:                 csrf.getToken());
```

## backend/src/main/java/dev/vmarket/shared/RequestBodyLimits.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/shared/RequestBodyLimits.java)

```text
5:     public static final int CSV_MAX_BYTES = 5_000_000;
6:     public static final int JSON_MAX_BYTES = 65_536;
```

## backend/src/main/java/dev/vmarket/shared/SecurityConfiguration.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/shared/SecurityConfiguration.java)

```text
11: import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
12: import org.springframework.security.web.csrf.HttpSessionCsrfTokenRepository;
13: import org.springframework.session.web.http.CookieSerializer;
14: import org.springframework.session.web.http.DefaultCookieSerializer;
24:     CookieSerializer sessionCookie(@Value("${auth.secure-cookie:true}") boolean secure) {
25:         var cookie = new DefaultCookieSerializer();
26:         cookie.setCookieName("VMARKET_SESSION");
27:         cookie.setUseHttpOnlyCookie(true);
28:         cookie.setUseSecureCookie(secure);
29:         cookie.setSameSite("Lax");
30:         cookie.setCookiePath("/");
31:         return cookie;
41:         return http.csrf(csrf -> csrf.csrfTokenRepository(new HttpSessionCsrfTokenRepository())
42:                         .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler())
43:                         .requireCsrfProtectionMatcher(request ->
65:                         .hasRole("OPERATOR")
76:                 .addFilterBefore(bffAuthenticationFilter, org.springframework.security.web.csrf.CsrfFilter.class)
```

## backend/src/main/java/dev/vmarket/shared/SessionAccountRefreshFilter.java

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/java/dev/vmarket/shared/SessionAccountRefreshFilter.java)

```text
27:                 var account = users.loadUserByUsername(authentication.getName());
28:                 if (!account.isEnabled()) throw new UsernameNotFoundException("Account disabled");
```

## backend/src/main/resources/db/migration/V14__supplier_integration_profiles.sql

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/backend/src/main/resources/db/migration/V14__supplier_integration_profiles.sql)

```text
16: CREATE FUNCTION protect_integration_profile_definition() RETURNS trigger LANGUAGE plpgsql AS $$
30:     FOR EACH ROW EXECUTE FUNCTION protect_integration_profile_definition();
32: INSERT INTO integration_profile(profile_id,version,encoding,vendor_code,mapping,sku_normalization,active,created_by,updated_by)
```

## lib/backend-proxy.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/lib/backend-proxy.ts)

```text
4:   bffSecret?: string;
5:   opsSecret?: string;
16:   "cookie",
17:   "x-csrf-token",
25: async function withinDeadline<T>(milliseconds: number, task: (signal: AbortSignal) => Promise<T>): Promise<T> {
39: async function readBoundedBody(request: Request, limit: number, signal: AbortSignal): Promise<Uint8Array<ArrayBuffer> | undefined> {
49: async function readBoundedStream(stream: ReadableStream<Uint8Array> | null, limit: number,
83: export function buildBackendHeaders(
92:   if (credentials.bffSecret) {
93:     headers.set("X-V-Market-BFF-Secret", credentials.bffSecret);
95:   if (credentials.opsSecret) {
96:     headers.set("X-V-Market-Ops-Secret", credentials.opsSecret);
101: export async function proxyToBackend(
128:     bffSecret: process.env.BFF_SHARED_SECRET,
129:     opsSecret: options.operations ? process.env.VMARKET_OPS_SECRET : undefined,
137:           ? 5_000_000 : 65_536, signal));
154:       const bytes = await readBoundedStream(response.body, 5_000_000, signal);
184:   for (const cookie of response.headers.getSetCookie()) {
185:     responseHeaders.append("Set-Cookie", cookie);
```

## lib/operations-api.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/lib/operations-api.ts)

```text
3: export type MigrationSummary = {
19: export type IntegrationProfile = {
24: export type ValidationError = { rowNumber: number; reason: string };
25: export type SupplierPreview = {
31: export type ImportInspection = {
36: export async function loadIntegrationProfiles(signal?: AbortSignal): Promise<IntegrationProfile[]> {
39: function onboardingPath(id: string, version: number, action: "preview" | "confirm"): string {
42: export async function previewSupplier(id: string, version: number, csv: string | ArrayBuffer): Promise<SupplierPreview> {
47: export async function confirmSupplier(id: string, version: number, sourceName: string, csv: string | ArrayBuffer, receipt: string): Promise<MigrationSummary> {
52: export async function inspectImport(jobId: string, signal?: AbortSignal): Promise<ImportInspection> {
56: export type Discrepancy = {
66: export type ReconciliationReport = {
77: export type OperationsOrder = {
87: async function readOrThrow<T>(response: Response): Promise<T> {
95: export function selectImportPayload(
107: export async function loadMigrationJobs(signal?: AbortSignal): Promise<MigrationSummary[]> {
113: export function importPollingInterval(jobs: ReadonlyArray<Pick<MigrationSummary,"status">> | undefined,failed: boolean): 2000 | false {
117: export async function loadInventorySnapshot(signal?: AbortSignal): Promise<string> {
126: export async function restartImport(jobId: string): Promise<MigrationSummary> {
130: export async function uploadLegacyCatalog(
149: export async function loadReconciliations(
157: export async function runReconciliation(
169: export async function loadOperationsOrders(signal?: AbortSignal): Promise<OperationsOrder[]> {
173: export async function advanceFulfillment(
```

## lib/operator-session.ts

[Pinned source](https://github.com/vietdungnguyen2005/Project2/blob/32d82862526754b46efb774327ccc4774a4decf7/lib/operator-session.ts)

```text
1: export type OperatorSession = {
5:   csrfToken: string;
8: export async function getOperatorSession(signal?: AbortSignal): Promise<OperatorSession> {
14: export async function operatorFetch(url: string, init: RequestInit = {}): Promise<Response> {
19:     headers.set("X-CSRF-TOKEN", session.csrfToken);
```

## Existing Java integration test names

```text
41: void supplierEnrichmentDoesNotChangeLegacyUnknownColumnCompatibility() {
56: void supplierProfileMigrationPreservesLegacyHistoryAndMakesDefinitionsImmutable() {
89: void profilesExposeRequiredFieldsAndApprovedTypeRangePolicy() throws Exception {
101: void onboardingPreservesOperatorCsrfAndOpsSecretBoundariesAndBlocksUnsafeRestarts() throws Exception {
136: void supplierDatabaseFailureRollsBackChunkAndUsesOnlyTheExistingSafeRestart() {
190: void concurrentSupplierConfirmationsShareOneDurableIdentityAndOneMovement() throws Exception {
221: void seededSupplierOnboardingBenchmarkProducesMeasuredImportAndReconciliationEvidence() throws Exception {
309: void stagedSupplierSnapshotRejectsLaterCatalogChangesAndInactiveProfilesCannotConfirm() {
340: void supplierProfilesDecodeOriginalCp932AndRejectWrongEncodingHeadersAndOversizedInputsBeforeStaging() {
373: void previewConfirmationIsBoundToTheOperatorBytesAndCurrentCatalogState() {
405: void identicalSupplierBytesCannotReplayThroughAnotherProfileVersionOrLegacyEndpoint() {
438: void oversizedRejectedSupplierCellsCannotPoisonTheValidRowsStagingTransaction() {
455: void importInspectionExposesSafeReasonsAndWorkStateNotRawPayload() throws Exception {
479: void confirmedSupplierPreviewUsesExistingDurableImportAndRawByteDedup() throws Exception {
536: void supplierPreviewMapsAndQuarantinesRowsWithoutAnyBusinessWrites() throws Exception {
571: void operatorPublishesImmutableProfileVersionAndAuditsActivation() throws Exception {
608: void supplierProfilesExposeVersionedMappingsWithoutCreatingImportWork() throws Exception {
625: void checkoutKeyLockAlsoTimesOutWithoutExecutingASecondSale() throws Exception {
667: void checkoutStatementTimeoutRollsBackEarlierWritesWhenAuditStalls() throws Exception {
710: void jdbcConnectionAndSocketWaitingHaveExplicitConfigurationBudgets() {
722: void anExhaustedConnectionPoolReturnsPromptlyWithoutStartingAnotherCheckout() throws Exception {
757: void checkoutStockLockWaitIsBoundedAndTheSameKeyCanBeUsedAfterRollback() throws Exception {
799: void concurrentCreateAndCloseCanNeverBothSucceedForTheSameGuestKey() throws Exception {
842: void closingAnExistingOrderIsRejectedAndClosuresDoNotAffectAnotherGuestScope() throws Exception {
864: void closingUnusedIntentsHasASerializedCapacityLimitButExistingClosuresRemainReadable() throws Exception {
899: void closingAnUnusedCheckoutPreventsALateOriginalRequestFromCreatingAnOrder() throws Exception {
926: void aGuestCanRecoverItsCommittedCheckoutWithoutResendingCustomerData() throws Exception {
947: void replayCleanupIsBoundedAndSkipsAnExpiredOrderLockedByAnotherTransaction() throws Exception {
997: void corruptReplayStorageCannotRotateTheTrackingCapabilityOrRepeatTheSale() throws Exception {
1022: void malformedOrMissingGuestCapabilitiesCannotCreateCheckoutWork() throws Exception {
1046: void expiredReplayCiphertextIsPurgedWithoutDeletingTheOrderKeyOrTrackingHash() throws Exception {
1075: void aHistoricalUnscopedKeyRequiresReviewInsteadOfCreatingAnotherScopedOrder() throws Exception {
1101: void anExpiredCheckoutKeyCannotCreateAnotherOrderOrInvalidateItsOriginalTrackingLink() throws Exception {
1126: void trackingCapabilityIsIndependentOfTheCheckoutKeyButStableOnRetry() throws Exception {
1144: void differentGuestCapabilitiesCannotReplayEachOthersCheckoutKey() throws Exception {
1173: void unavailableRedisDoesNotPreventDatabaseCatalogReadsOrCorrectCheckout() throws Exception {
1188: void catalogCacheContainsOnlyMetadataAndCannotKeepAnInactiveProductVisible() throws Exception {
1208: void theOneThousandRowBoundaryIsAcceptedWithoutExecutingInTheRequest() throws Exception {
1223: void malformedCp932AlsoRejectsTheWholeFileBeforeStaging() throws Exception {
1240: void oversizedCsvHasAnExplicitPayloadLimitResponse() throws Exception {
1251: void byteIdenticalUploadsWithDifferentDeclaredEncodingsConflict() throws Exception {
1265: void aDuplicateUploadCannotBypassEncodingValidation() throws Exception {
1279: void anImportOverOneThousandDataRowsIsRejectedBeforeStaging() throws Exception {
1295: void extraCsvValuesAreRejectedInsteadOfSilentlyDiscarded() throws Exception {
1307: void duplicateHeadersCannotSilentlyChooseOneOfTwoStockColumns() throws Exception {
1319: void malformedUtf8IsRejectedBeforeAnyImportJobIsStaged() throws Exception {
1350: void aWarmCatalogCacheCannotHideStockConsumedByCheckout() throws Exception {
1361: void unknownBatchMetadataIsBlockedRatherThanBlindlyRestarted() {
1390: void aRecoveryFailureDoesNotStarveOtherReadyJobs() {
1434: void repeatedOwnerLossStopsAfterThreeRecoveriesAndRequiresReview() {
1468: void recoveryAcknowledgesCompletedMetadataWithoutLaunchingAnotherExecution() {
1513: void recoveryMetadataRetirementAndGenerationRevocationRollBackTogetherOnFailure() {
1564: void recoveryResumesThePendingRowAfterFiftyRealStockMovementsAlreadyCommitted() throws Exception {
1626: void recoveryCanHandleAnotherCrashAfterClaimButBeforeANewExecutionIsCreated() {
1664: void recoveryDoesNotStealALiveLeaseOrAJobRowHeldByAnInFlightTransaction() throws Exception {
1708: void recoveredWorkerCannotRewriteJobStepOrExecutionContextMetadata() {
1785: void dispatcherRecoversAnExpiredStartedExecutionWithoutRepeatingItsCommittedMovement() {
1822: void completedImportAlsoCompletesItsFencedBatchMetadataBeforeReleasingOwnership() throws Exception {
1850: void importMetadataCannotCreateAnExecutionWithoutItsCurrentWorkerScope() {
1872: void dispatchMigrationDoesNotEnqueueExistingSynchronousReadyWork() {
1912: void competingDispatchersConsumeAQueuedJobOnlyOnce() throws Exception {
1951: void concurrentDuplicateAsyncUploadsCreateOneDurableJobInsteadOfFailingWithDuplicateChecksum() throws Exception {
2005: void asyncRestartQueuesExistingFailedJobAndOnlyTheDispatcherAppliesIt() throws Exception {
2048: void dispatcherConsumesCommittedAsyncWorkButLeavesLegacyReadyWorkAlone() throws Exception {
2090: void asynchronousUploadReturnsDurablyStagedWorkWithoutRunningItInTheRequest() throws Exception {
2126: void aStagingFailureRollsBackTheJobAndItsDurableWorkTogether() throws Exception {
2168: void workMigrationPreservesOldJobsWithoutInventingOwnersForActiveExecutions() {
2209: void twoWorkersCompetingForReadyWorkProduceOneOwnerAndOneMovement() throws Exception {
2246: void losingTheLeaseInsideAChunkRollsBackStockProofAndAfterCommitEffects() {
2298: void expiredOwnershipCanBeFencedWithoutLettingTheOldWorkerAdoptOrFailTheNewGeneration() {
2345: void workerTokensAreNotStoredInBatchParametersThatTheLauncherLogs() throws Exception {
2367: void aChunkWithoutAWorkerClaimCannotChangeInventory() {
2380: void anUploadedImportHasADurableWorkRecordAndTerminalOutcome() throws Exception {
2410: void aSecondRestartIsRejectedPromptlyWhileTheFirstWorkerHoldsTheJobRow() throws Exception {
2484: void batchObservationMetersDoNotCollideWithLegacyBatchMeters() throws Exception {
2502: void aFailed120RowImportRestartsTheSameInstanceWithoutRepeatingCommittedMovements() throws Exception {
2585: void aFailedBatchExecutionIsReportedAsFailedInsteadOfLeavingAStagedJob() throws Exception {
2619: void checkoutAndStagedSnapshotOnlyProduceTheTwoLegalSerializedOutcomes() throws Exception {
2668: void stockPolicyMigrationPreservesHistoryWithoutInventingVersionProof() {
2758: void movementFailureRollsBackTheWholeChunkIncludingProofMetricsAndInvalidation() {
2811: void aNegativeStockVersionIsQuarantinedInsteadOfFailingTheWholeUpload() throws Exception {
2828: void unversionedLegacyFilesOnlyChangeMetadataAndCannotClaimStockVerification() throws Exception {
2865: void aLegitimateSaleAfterImportIsChangedSinceImportNotCorruption() throws Exception {
2902: void operatorsCanExportCurrentVersionsButAnonymousCallersCannot() throws Exception {
2921: void duplicateCanonicalSkusInOneSnapshotAreAllQuarantined() throws Exception {
2943: void anOldVersionedStockSnapshotCannotRestoreAlreadySoldInventory() throws Exception {
2989: void concurrentSessionAttributeInsertionDoesNotFailARequest() {
3009: void operationsRequireAUserSessionEvenWithTrustedServiceCredentials() throws Exception {
3041: void repeatedFailedLoginsAreRateLimited() throws Exception {
3062: void disablingAnOperatorRevokesAnExistingSession() throws Exception {
3116: void sessionsEnforceRoleCsrfAndLogout() throws Exception {
3155: void operatorLoginRotatesTheSessionAndAuthorizesOperations() throws Exception {
3201: void clearCatalogCache() {
3210: void contextProvidesCatalogApi() {
3215: void mutationsRejectRequestsThatBypassTheCloudflareBff() throws Exception {
3224: void catalogComesFromTheCanonicalDatabase() throws Exception {
3233: void catalogResponseIsCachedInRedis() throws Exception {
3240: void checkoutCreatesATrackedOrderAndConsumesInventoryAtomically() throws Exception {
3277: void idempotentCheckoutReturnsTheSameOrderWithoutDoubleDecrementingStock() throws Exception {
3289: void concurrentCheckoutCannotOversellInventory() throws Exception {
3321: void simultaneousDuplicateCheckoutReturnsOneOrderAndConsumesStockOnce() throws Exception {
3346: void rejectsReusingACheckoutKeyForDifferentQuantities() throws Exception {
3360: void fingerprintMigrationPreservesAnExistingLegacyOrder() {
3392: void customerCanTrackAnOrderOnlyWithItsOpaqueToken() throws Exception {
3422: void operatorCanAdvanceFulfillmentWithAnAuditedTransition() throws Exception {
3486: void legacyImportAppliesValidRowsAndQuarantinesInvalidRows() throws Exception {
3514: void legacyImportDecodesJapaneseCp932Feeds() throws Exception {
3535: void reconciliationMakesPostMigrationDriftVisible() throws Exception {
```

## Migration inventory

- V10__guest_checkout_scope.sql
- V11__protected_checkout_replay.sql
- V12__checkout_replay_retention_index.sql
- V13__closed_checkout_intents.sql
- V14__supplier_integration_profiles.sql
- V1__commerce_baseline.sql
- V2__order_privacy_acknowledgement.sql
- V3__checkout_request_fingerprint.sql
- V4__operator_sessions.sql
- V5__versioned_stock_imports.sql
- V6__reconciliation_baseline_scope.sql
- V7__durable_import_work.sql
- V8__import_dispatch_intent.sql
- V9__import_recovery_audit.sql
