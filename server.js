import com.corundumstudio.socketio.*;
import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.*;

@Component
public class KenoServer {

    private SocketIOServer server;
    private int timeLeft = 90;
    private String gameStatus = "BETTING";
    private final List<Map<String, Object>> currentBets = new CopyOnWriteArrayList<>();

    @PostConstruct
    public void init() {
        Configuration config = new Configuration();
        config.setHostname("0.0.0.0");
        config.setPort(3000); // Socket.io የሚሰራበት ፖርት

        server = new SocketIOServer(config);

        // --- ውርርድ መቀበያ ---
        server.addEventListener("placeBet", Map.class, (client, data, ackSender) -> {
            if (gameStatus.equals("BETTING")) {
                currentBets.add(data);
                client.sendEvent("betSuccess", "ውርርድዎ ተመዝግቧል!");
            } else {
                client.sendEvent("error", "ይቅርታ፣ ውርርድ ተዘግቷል።");
            }
        });

        // --- የገንዘብ ማውጫ ጥያቄ (Withdraw) ---
        server.addEventListener("withdrawRequest", Map.class, (client, data, ackSender) -> {
            // እዚህ ጋር ወደ አድሚን ቴሌግራም መልዕክት የሚልክ ኮድ ይገባል
            System.out.println("Withdraw Request: " + data);
        });

        server.start();
        startGameLoop();
    }

    private void startGameLoop() {
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(() -> {
            timeLeft--;

            if (timeLeft <= 0) {
                if (gameStatus.equals("BETTING")) {
                    gameStatus = "DRAWING";
                    timeLeft = 30;
                    runDrawProcess();
                } else {
                    gameStatus = "BETTING";
                    timeLeft = 90;
                    currentBets.clear();
                }
            }

            // መረጃውን ለሁሉም ተጫዋቾች መላክ
            Map<String, Object> update = new HashMap<>();
            update.put("timer", formatTime(timeLeft));
            update.put("status", gameStatus);
            server.getBroadcastOperations().sendEvent("gameUpdate", update);

        }, 0, 1, TimeUnit.SECONDS);
    }

    private void runDrawProcess() {
        List<Integer> winningNumbers = new ArrayList<>();
        Random random = new Random();
        while (winningNumbers.size() < 20) {
            int n = random.nextInt(80) + 1;
            if (!winningNumbers.contains(n)) winningNumbers.add(n);
        }
        // እጣውን ለሁሉም መላክ
        server.getBroadcastOperations().sendEvent("drawResult", winningNumbers);
    }

    private String formatTime(int totalSecs) {
        return String.format("%02d:%02d", totalSecs / 60, totalSecs % 60);
    }
}
