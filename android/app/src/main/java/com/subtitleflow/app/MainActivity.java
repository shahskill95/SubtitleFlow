package com.subtitleflow.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int PICK_VIDEO = 71;
    private static final String PREFS = "subtitle_flow";
    private static final int BG = Color.rgb(10, 16, 32);
    private static final int CARD = Color.rgb(20, 30, 49);
    private static final int CARD_LIGHT = Color.rgb(27, 40, 62);
    private static final int MINT = Color.rgb(114, 230, 202);
    private static final int TEXT = Color.rgb(244, 247, 252);
    private static final int MUTED = Color.rgb(154, 170, 191);
    private static final int ORANGE = Color.rgb(255, 183, 132);

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private Uri selectedVideo;
    private String selectedName = "";
    private EditText serverInput;
    private TextView selectedFileText;
    private TextView statusText;
    private TextView statusDot;
    private Button chooseButton;
    private Button createButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        buildScreen();
    }

    private void buildScreen() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(22), dp(18), dp(22), dp(30));
        scroll.addView(page, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setOrientation(LinearLayout.HORIZONTAL);

        TextView logo = new TextView(this);
        logo.setText("S");
        logo.setTextColor(BG);
        logo.setTextSize(23);
        logo.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        logo.setGravity(Gravity.CENTER);
        logo.setBackground(round(MINT, 16));
        header.addView(logo, new LinearLayout.LayoutParams(dp(46), dp(46)));

        LinearLayout brand = new LinearLayout(this);
        brand.setOrientation(LinearLayout.VERTICAL);
        brand.setPadding(dp(12), 0, 0, 0);
        TextView brandName = text("SUBTITLEFLOW", 15, TEXT, true);
        brandName.setLetterSpacing(0.10f);
        brand.addView(brandName);
        TextView brandTag = text("VIDEO  →  RUSSIAN SRT", 10, MUTED, true);
        brandTag.setLetterSpacing(0.12f);
        LinearLayout.LayoutParams tagParams = new LinearLayout.LayoutParams(-2, -2);
        tagParams.topMargin = dp(4);
        brand.addView(brandTag, tagParams);
        header.addView(brand, new LinearLayout.LayoutParams(0, -2, 1));

        TextView localBadge = text("WI-FI", 10, MINT, true);
        localBadge.setGravity(Gravity.CENTER);
        localBadge.setPadding(dp(12), dp(8), dp(12), dp(8));
        localBadge.setBackground(round(Color.rgb(18, 55, 57), 50));
        header.addView(localBadge);
        page.addView(header);

        TextView eyebrow = text("ТВОЙ ВИДЕО-ПЕРЕВОДЧИК", 11, MINT, true);
        eyebrow.setLetterSpacing(0.14f);
        LinearLayout.LayoutParams eyebrowParams = new LinearLayout.LayoutParams(-2, -2);
        eyebrowParams.topMargin = dp(34);
        page.addView(eyebrow, eyebrowParams);

        TextView title = text("Видео.\nРусские субтитры.", 32, TEXT, true);
        title.setLineSpacing(dp(1), 1.0f);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(-1, -2);
        titleParams.topMargin = dp(10);
        page.addView(title, titleParams);

        TextView intro = text("Выбери ролик на телефоне — компьютер распознает речь, переведёт её и вернёт готовый файл .SRT.", 14, MUTED, false);
        intro.setLineSpacing(dp(4), 1.05f);
        LinearLayout.LayoutParams introParams = new LinearLayout.LayoutParams(-1, -2);
        introParams.topMargin = dp(12);
        introParams.bottomMargin = dp(24);
        page.addView(intro, introParams);

        // Connection card
        LinearLayout connectionCard = card();
        page.addView(connectionCard, matchWrap());
        connectionCard.addView(sectionLabel("01", "ПОДКЛЮЧЕНИЕ К КОМПЬЮТЕРУ"));
        TextView serverHint = text("Запусти start_subtitleflow.bat на Windows. В окне появится адрес компьютера — вставь его сюда. Телефон и ПК должны быть в одной сети Wi-Fi.", 12, MUTED, false);
        serverHint.setLineSpacing(dp(3), 1.0f);
        LinearLayout.LayoutParams serverHintParams = new LinearLayout.LayoutParams(-1, -2);
        serverHintParams.topMargin = dp(10);
        connectionCard.addView(serverHint, serverHintParams);

        serverInput = new EditText(this);
        serverInput.setSingleLine(true);
        serverInput.setTextColor(TEXT);
        serverInput.setHintTextColor(Color.rgb(118, 134, 155));
        serverInput.setHint("Полный адрес из окна SubtitleFlow на ПК");
        serverInput.setTextSize(14);
        serverInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        serverInput.setPadding(dp(14), dp(13), dp(14), dp(13));
        serverInput.setBackground(round(CARD_LIGHT, 12));
        String savedUrl = getSharedPreferences(PREFS, MODE_PRIVATE).getString("server", "");
        serverInput.setText(savedUrl);
        LinearLayout.LayoutParams inputParams = new LinearLayout.LayoutParams(-1, dp(50));
        inputParams.topMargin = dp(14);
        connectionCard.addView(serverInput, inputParams);

        // Video card
        LinearLayout videoCard = card();
        LinearLayout.LayoutParams videoCardParams = matchWrap();
        videoCardParams.topMargin = dp(14);
        page.addView(videoCard, videoCardParams);
        videoCard.addView(sectionLabel("02", "ВЫБОР ВИДЕО"));
        TextView videoHint = text("Поддерживаются обычные видеофайлы, например MP4 и MOV.", 12, MUTED, false);
        LinearLayout.LayoutParams videoHintParams = new LinearLayout.LayoutParams(-1, -2);
        videoHintParams.topMargin = dp(8);
        videoCard.addView(videoHint, videoHintParams);

        chooseButton = makeButton("＋   Выбрать видео", false);
        LinearLayout.LayoutParams chooseParams = new LinearLayout.LayoutParams(-1, dp(52));
        chooseParams.topMargin = dp(14);
        videoCard.addView(chooseButton, chooseParams);
        chooseButton.setOnClickListener(v -> pickVideo());

        selectedFileText = text("Файл пока не выбран", 12, MUTED, false);
        selectedFileText.setMaxLines(2);
        LinearLayout.LayoutParams selectedParams = new LinearLayout.LayoutParams(-1, -2);
        selectedParams.topMargin = dp(10);
        videoCard.addView(selectedFileText, selectedParams);

        // Output card
        LinearLayout outputCard = card();
        LinearLayout.LayoutParams outputParams = matchWrap();
        outputParams.topMargin = dp(14);
        page.addView(outputCard, outputParams);
        outputCard.addView(sectionLabel("03", "РЕЗУЛЬТАТ"));
        LinearLayout outRow = new LinearLayout(this);
        outRow.setGravity(Gravity.CENTER_VERTICAL);
        outRow.setPadding(0, dp(13), 0, 0);
        TextView fileGlyph = text("SRT", 13, MINT, true);
        fileGlyph.setGravity(Gravity.CENTER);
        fileGlyph.setBackground(round(Color.rgb(18, 55, 57), 10));
        outRow.addView(fileGlyph, new LinearLayout.LayoutParams(dp(48), dp(42)));
        LinearLayout outText = new LinearLayout(this);
        outText.setOrientation(LinearLayout.VERTICAL);
        outText.setPadding(dp(12), 0, 0, 0);
        outText.addView(text("Русские субтитры", 14, TEXT, true));
        TextView outCaption = text("Тайм-коды сохраняются · UTF-8", 11, MUTED, false);
        LinearLayout.LayoutParams outCaptionParams = new LinearLayout.LayoutParams(-2, -2);
        outCaptionParams.topMargin = dp(4);
        outText.addView(outCaption, outCaptionParams);
        outRow.addView(outText);
        outputCard.addView(outRow);

        createButton = makeButton("Создать русские субтитры   →", true);
        LinearLayout.LayoutParams createParams = new LinearLayout.LayoutParams(-1, dp(58));
        createParams.topMargin = dp(20);
        page.addView(createButton, createParams);
        createButton.setOnClickListener(v -> startProcessing());

        LinearLayout statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.HORIZONTAL);
        statusCard.setGravity(Gravity.CENTER_VERTICAL);
        statusCard.setPadding(dp(14), dp(13), dp(14), dp(13));
        statusCard.setBackground(round(CARD, 14));
        LinearLayout.LayoutParams statusParams = matchWrap();
        statusParams.topMargin = dp(12);
        page.addView(statusCard, statusParams);
        statusDot = text("●", 12, MUTED, true);
        statusCard.addView(statusDot);
        statusText = text("Готово к работе. Сначала подключи компьютер.", 12, MUTED, false);
        LinearLayout.LayoutParams statusTextParams = new LinearLayout.LayoutParams(0, -2, 1);
        statusTextParams.leftMargin = dp(9);
        statusCard.addView(statusText, statusTextParams);

        TextView footer = text("ОБРАБОТКА НА ТВОЁМ ПК  ·  БЕЗ ОБЛАЧНОГО ХРАНИЛИЩА", 9, Color.rgb(104, 120, 143), true);
        footer.setGravity(Gravity.CENTER);
        footer.setLetterSpacing(0.07f);
        LinearLayout.LayoutParams footerParams = new LinearLayout.LayoutParams(-1, -2);
        footerParams.topMargin = dp(22);
        page.addView(footer, footerParams);

        setContentView(scroll);
    }

    private LinearLayout card() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(16), dp(16), dp(16), dp(16));
        box.setBackground(round(CARD, 18));
        return box;
    }

    private View sectionLabel(String number, String label) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        TextView num = text(number, 11, MINT, true);
        num.setGravity(Gravity.CENTER);
        num.setBackground(round(Color.rgb(18, 55, 57), 8));
        row.addView(num, new LinearLayout.LayoutParams(dp(30), dp(26)));
        TextView title = text(label, 11, TEXT, true);
        title.setLetterSpacing(0.08f);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(-2, -2);
        titleParams.leftMargin = dp(10);
        row.addView(title, titleParams);
        return row;
    }

    private Button makeButton(String label, boolean primary) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(14);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setGravity(Gravity.CENTER);
        button.setPadding(dp(12), 0, dp(12), 0);
        button.setTextColor(primary ? BG : TEXT);
        button.setBackground(round(primary ? MINT : CARD_LIGHT, 14));
        return button;
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(size);
        tv.setTextColor(color);
        tv.setTypeface(Typeface.DEFAULT, bold ? Typeface.BOLD : Typeface.NORMAL);
        return tv;
    }

    private GradientDrawable round(int color, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(radiusDp));
        return d;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void pickVideo() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("video/*");
        startActivityForResult(intent, PICK_VIDEO);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_VIDEO && resultCode == RESULT_OK && data != null && data.getData() != null) {
            selectedVideo = data.getData();
            selectedName = getDisplayName(selectedVideo);
            selectedFileText.setText("Выбрано: " + selectedName);
            selectedFileText.setTextColor(MINT);
            setStatus("Видео выбрано. Можно запускать обработку.", MINT);
        }
    }

    private String getDisplayName(Uri uri) {
        String name = "video.mp4";
        try (Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) name = cursor.getString(index);
            }
        } catch (Exception ignored) { }
        return name == null ? "video.mp4" : name;
    }

    private void startProcessing() {
        if (selectedVideo == null) {
            setStatus("Сначала выбери видеофайл.", ORANGE);
            return;
        }
        String baseUrl = serverInput.getText().toString().trim();
        while (baseUrl.endsWith("/")) baseUrl = baseUrl.substring(0, baseUrl.length() - 1);
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            setStatus("Введи полный адрес из окна SubtitleFlow на ПК.", ORANGE);
            return;
        }
        String accessKey = "";
        int keyPos = baseUrl.indexOf("?key=");
        if (keyPos >= 0) {
            accessKey = baseUrl.substring(keyPos + 5);
            baseUrl = baseUrl.substring(0, keyPos);
        }
        while (baseUrl.endsWith("/")) baseUrl = baseUrl.substring(0, baseUrl.length() - 1);
        if (accessKey.isEmpty()) {
            setStatus("В адресе не найден key. Скопируй полный адрес из окна SubtitleFlow на ПК.", ORANGE);
            return;
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("server", baseUrl + "/?key=" + accessKey).apply();
        final String server = baseUrl;
        final String appKey = accessKey;
        final Uri videoUri = selectedVideo;
        final String videoName = selectedName;

        createButton.setEnabled(false);
        chooseButton.setEnabled(false);
        setStatus("Подготавливаю видео для отправки…", MINT);

        executor.execute(() -> {
            File uploadFile = null;
            HttpURLConnection connection = null;
            try {
                uploadFile = File.createTempFile("subtitleflow_upload_", ".bin", getCacheDir());
                try (InputStream input = getContentResolver().openInputStream(videoUri);
                     OutputStream output = new FileOutputStream(uploadFile)) {
                    if (input == null) throw new IllegalStateException("Не удалось открыть видеофайл.");
                    byte[] buffer = new byte[64 * 1024];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                }

                final long sizeMb = Math.max(1, uploadFile.length() / (1024 * 1024));
                updateStatus("Отправляю видео на компьютер (" + sizeMb + " МБ)…", MINT);

                URL url = new URL(server + "/transcribe");
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setConnectTimeout(20000);
                connection.setReadTimeout(0);
                connection.setRequestProperty("Content-Type", "application/octet-stream");
                connection.setRequestProperty("X-App-Key", appKey);
                connection.setRequestProperty("X-Filename", URLEncoder.encode(videoName, "UTF-8"));
                connection.setRequestProperty("X-Model", "base");
                connection.setRequestProperty("X-Language", "auto");
                connection.setFixedLengthStreamingMode(uploadFile.length());

                try (InputStream input = new java.io.FileInputStream(uploadFile);
                     OutputStream output = connection.getOutputStream()) {
                    byte[] buffer = new byte[64 * 1024];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                }

                updateStatus("Компьютер распознаёт речь и переводит её. Не закрывай приложение…", MINT);
                int code = connection.getResponseCode();
                InputStream responseStream = code >= 200 && code < 300
                        ? connection.getInputStream() : connection.getErrorStream();
                byte[] response = readAll(responseStream);
                if (code < 200 || code >= 300) {
                    String message = new String(response, StandardCharsets.UTF_8);
                    throw new IllegalStateException("Сервер ответил " + code + ": " + message);
                }
                if (response.length == 0) throw new IllegalStateException("Сервер вернул пустой файл.");

                String outName = outputName(videoName);
                Uri savedUri = saveToDownloads(outName, response);
                updateSuccess("Готово! Русские субтитры сохранены в Загрузки: " + outName);
            } catch (Exception e) {
                String message = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
                updateError("Не получилось обработать видео. " + message + " Проверь адрес сервера и Wi-Fi.");
            } finally {
                if (connection != null) connection.disconnect();
                if (uploadFile != null) uploadFile.delete();
                mainHandler.post(() -> {
                    createButton.setEnabled(true);
                    chooseButton.setEnabled(true);
                });
            }
        });
    }

    private byte[] readAll(InputStream input) throws Exception {
        if (input == null) return new byte[0];
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
            return out.toByteArray();
        }
    }

    private String outputName(String sourceName) {
        String base = sourceName;
        int dot = base.lastIndexOf('.');
        if (dot > 0) base = base.substring(0, dot);
        base = base.replaceAll("[^\\p{L}\\p{N}._ -]", "_").trim();
        if (base.isEmpty()) base = "subtitles";
        return base + "_ru.srt";
    }

    private Uri saveToDownloads(String name, byte[] content) throws Exception {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, name);
        values.put(MediaStore.Downloads.MIME_TYPE, "application/x-subrip");
        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
        values.put(MediaStore.Downloads.IS_PENDING, 1);
        Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("Не удалось создать файл в папке Загрузки.");
        try (OutputStream output = getContentResolver().openOutputStream(uri)) {
            if (output == null) throw new IllegalStateException("Не удалось записать SRT-файл.");
            output.write(content);
            output.flush();
        } catch (Exception e) {
            getContentResolver().delete(uri, null, null);
            throw e;
        }
        ContentValues ready = new ContentValues();
        ready.put(MediaStore.Downloads.IS_PENDING, 0);
        getContentResolver().update(uri, ready, null, null);
        return uri;
    }

    private void setStatus(String message, int color) {
        statusText.setText(message);
        statusText.setTextColor(MUTED);
        statusDot.setTextColor(color);
    }

    private void updateStatus(String message, int color) {
        mainHandler.post(() -> setStatus(message, color));
    }

    private void updateSuccess(String message) {
        mainHandler.post(() -> {
            statusText.setText(message);
            statusText.setTextColor(MINT);
            statusDot.setTextColor(MINT);
        });
    }

    private void updateError(String message) {
        mainHandler.post(() -> {
            statusText.setText(message);
            statusText.setTextColor(ORANGE);
            statusDot.setTextColor(ORANGE);
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }
}
