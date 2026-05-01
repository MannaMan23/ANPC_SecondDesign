clc; close all; clear all;

filename = "C:\Users\Marianna\Documents\LTspice\Simulazioni_Automatizzate\Modello_RoHM_Vout\Completo_RoHM.txt";

% Se il file NON ha header (solo numeri), allora:
T = readtable(filename, 'HeaderLines', 0);

% Estrazione colonne come vettori numerici
time = T{:,1};    % prima colonna
Vout = T{:,2};    % seconda colonna

figure;
plot(time*1e6, Vout, 'LineWidth', 1.7,'Color','[0 0 0.5]');   % tempo in microsecondi
set(gca, 'FontSize', 19, 'FontName', 'Helvetica', 'FontWeight', 'bold');
xlabel('Time [us]','FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 21);
ylabel('Vout [V]', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 21);
%title('ANPC Output Voltage', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize',23);
set(gca, 'FontSize',13, 'FontName', 'Helvetica');
%grid on;

% xlim([0 5]);  




% %filename = "C:\Users\Marianna\Documents\LTspice\Simulazioni_Automatizzate\Modello_RoHM\Paper_Grafici\GaN_ROHM_S_SK.txt";
% 
% T = readtable(filename, 'HeaderLines', 0);
% 
% time = T{:,1};    
% Vgs1 = T{:,2};    
% Vgs2 = T{:,4};
% c1 = [78 157 209]/255;
% c2 = [120 190 235]/255;
% 
% t_us = time * 1e6;
% Tmezzo = max(t_us)/2;
% idx = t_us <= Tmezzo;
% 
% figure('Position', [100 100 900 350]);   % <-- QUI
% 
% plot(t_us(idx), Vgs1(idx), 'LineWidth', 2.3, 'Color', c1); hold on;
% plot(t_us(idx), Vgs2(idx), 'LineWidth', 2.3);
% set(gca, 'FontSize', 19.9, 'FontName', 'Helvetica', 'FontWeight', 'bold');
% xlabel('Time [us]', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 23);
% ylabel('Gate Voltage [V]', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 23);
% lgd = legend('Vgs1','Vgs2');  % crea la legenda e cattura l’oggetto
% lgd.FontSize = 19;            % cambia la dimensione del font
% lgd.FontWeight = 'bold';      % font in grassetto
% % lgd.LineWidth = 1.5;   
% ylim([-5 10]);
% grid on;
% 
% 
% 
% 
% % % --- Primo plot ---
% % subplot(2,1,1);
% % title('ANPC Output Voltage', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize',23);
% % plot(time*1e6, Vgs1, 'LineWidth', 1.7);
% % set(gca, 'FontSize', 19, 'FontName', 'Helvetica', 'FontWeight', 'bold');
% % 
% % %xlabel('Time [us]','FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 18);
% % ylabel('Vgs1 [V]', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 18);
% % %title('M1 Control Loop Voltage', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize',20);
% % set(gca, 'FontSize', 13, 'FontName', 'Helvetica');
% % ylim([-10 10]);
% % grid on;
% % 
% % % --- Secondo plot ---
% % subplot(2,1,2);
% % plot(time*1e6, Vgs2, 'LineWidth', 1.7);
% % set(gca, 'FontSize', 19, 'FontName', 'Helvetica', 'FontWeight', 'bold');
% % 
% % xlabel('Time [us]','FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 21);
% % ylabel('Vgs2 [V]', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize', 21);
% % %title('M2 Control Loop Voltage', 'FontName', 'Helvetica', 'FontWeight', 'bold', 'FontSize',20);
% % set(gca, 'FontSize', 13, 'FontName', 'Helvetica');
% % ylim([-10 10]);
% % grid on;
% 
% 
% % sgtitle('ANPC Output Voltage','FontName','Helvetica','FontWeight','bold','FontSize',23);
% 
% 
% 
% 
% 
