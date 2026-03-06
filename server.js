import com.corundumstudio.socketio.*;
import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.*;

@Component
public class KenoSocketHandler {

    private SocketIOServer server;
    private int timeLeft = 90; // 1:30 ደቂቃ
    private String status = "BETTING";

    @PostConstruct
    public void startServer() {
        Configuration config = new Configuration();
        config.setHostname("0.0.0.0");
        config.setPort(3000); // ይህ ፖርት በRender/VPS ላይ ክፍት መሆን አለበት

        server = new SocketIOServer(config);

        // ተጫዋች ሲገናኝ
        server.addConnectListener(client -> {
            System.out.println("ተጫዋች ተገናኝቷል: " + client.getSessionId());
        });

        // ውርርድ መቀበያ
        server.addEventListener("placeBet", Map.class, (client, data, ackSender) -> {
            System.out.println("ውርርድ ደርሷል: " + data);
            // እዚህ ጋር የባላንስ ቼክ እና የ70/30 ሂሳብ ስሌት ይገባል
        });

        server.start();
        runGameLoop();
    }

    private void runGameLoop() {
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(() -> {
            if (timeLeft > 0) {
                timeLeft--;
            } else {
                // ሁኔታውን ቀይር
                if (status.equals("BETTING")) {
                    status = "DRAWING";
                    timeLeft = 30; // የዕጣ ሰዓት
                    generateAndSendDraw();
                } else {
                    status = "BETTING";
                    timeLeft = 90;
                }
            }

            // ለሁሉም ተጫዋቾች (Vercel ላይ ላሉት) መረጃ መላክ
            Map<String, Object> gameData = new HashMap<>();
            gameData.put("timer", formatTime(timeLeft));
            gameData.put("status", status);
            server.getBroadcastOperations().sendEvent("gameUpdate", gameData);

        }, 0, 1, TimeUnit.SECONDS);
    }

    private void generateAndSendDraw() {
        List<Integer> winningNumbers = new ArrayList<>();
        Random rand = new Random();
        while (winningNumbers.size() < 20) {
            int n = rand.nextInt(80) + 1;
            if (!winningNumbers.contains(n)) winningNumbers.add(n);
        }
        server.getBroadcastOperations().sendEvent("drawResult", winningNumbers);
    }

    private String formatTime(int secs) {
        return String.format("%02d:%02d", secs / 60, secs % 60);
    }
}
