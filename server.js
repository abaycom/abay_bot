import com.corundumstudio.socketio.*;
import org.springframework.stereotype.Service;
import org.telegram.telegrambots.bots.TelegramLongPollingBot;
import org.telegram.telegrambots.meta.api.methods.send.SendMessage;
import org.telegram.telegrambots.meta.api.objects.Update;

import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.*;

@Service
public class KenoGameServer extends TelegramLongPollingBot {

    private SocketIOServer socketServer;
    private int timeLeft = 90;
    private String status = "BETTING";
    private final String ADMIN_ID = "YOUR_ADMIN_ID"; // ያንተ ID
    private Map<Long, Double> balances = new ConcurrentHashMap<>();

    @PostConstruct
    public void startServer() {
        // 1. Socket.io Configuration
        Configuration config = new Configuration();
        config.setHostname("0.0.0.0");
        config.setPort(3000);
        socketServer = new SocketIOServer(config);

        // ተጫዋች ውርርድ ሲልክ
        socketServer.addEventListener("placeBet", Map.class, (client, data, ackSender) -> {
            String userId = data.get("userId").toString();
            double amount = Double.parseDouble(data.get("amount").toString());
            // እዚህ ጋር ባላንስ ቼክ ይደረጋል
            System.out.println("Bet received: " + userId + " Amount: " + amount);
        });

        socketServer.start();
        startGameLoop();
    }

    // 2. Game Loop (1:30 Betting + 30s Drawing)
    private void startGameLoop() {
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(() -> {
            timeLeft--;
            if (timeLeft <= 0) {
                if (status.equals("BETTING")) {
                    status = "DRAWING";
                    timeLeft = 30;
                    generateDraw();
                } else {
                    status = "BETTING";
                    timeLeft = 90;
                }
            }
            // ለሁሉም ተጫዋቾች መረጃ መላክ
            Map<String, Object> update = new HashMap<>();
            update.put("timer", formatTime(timeLeft));
            update.put("status", status);
            socketServer.getBroadcastOperations().sendEvent("gameUpdate", update);
        }, 0, 1, TimeUnit.SECONDS);
    }

    private void generateDraw() {
        List<Integer> winningNums = new ArrayList<>();
        while (winningNums.size() < 20) {
            int n = new Random().nextInt(80) + 1;
            if (!winningNums.contains(n)) winningNums.add(n);
        }
        socketServer.getBroadcastOperations().sendEvent("drawResult", winningNums);
        // የ 70/30 ክፍያ ሂሳብ እዚህ ይሰላል
    }

    private String formatTime(int s) {
        return String.format("%02d:%02d", s / 60, s % 60);
    }

    // 3. Telegram Bot Logic (Deposit/Withdraw)
    @Override
    public void onUpdateReceived(Update update) {
        if (update.hasMessage() && update.getMessage().hasPhoto()) {
            // ደረሰኝ ሲመጣ ለአድሚን መላክ
            SendMessage msg = new SendMessage(5049565154, "አዲስ ደረሰኝ መጥቷል ከ፡ " + update.getMessage().getFrom().getId());
            try { execute(msg); } catch (Exception e) { e.printStackTrace(); }
        }
    }

    @Override public String getBotUsername() { return "Hiaiethiopiabot"; }
    @Override public String getBotToken() { return "7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo"; }
}
