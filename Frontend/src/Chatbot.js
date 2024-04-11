import React, { useEffect, useRef, useState } from 'react';
import { Box, TextField, Button, Typography, Avatar, Link } from '@mui/material';
import './App.css';

function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [nameSubmitted, setNameSubmitted] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [chatEnded, setChatEnded] = useState(false);

  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    let intervalId;
    if (thinking) {
      // Initialisiere die "Denken"-Nachricht
      const thinkingMsg = { id: 'thinking', sender: 'bot' };
      setMessages(currentMessages => [...currentMessages, thinkingMsg]);

      let dotCount = 1;
      intervalId = setInterval(() => {
        dotCount = (dotCount % 3) + 1; // Zyklus durch 1-3
        setMessages(currentMessages =>
          currentMessages.map(msg =>
            msg.id === 'thinking' ? { ...msg, text: `Bot denkt nach${'.'.repeat(dotCount)}` } : msg
          )
        );
      }, 500);
    } else {
      setMessages(currentMessages => currentMessages.filter(msg => msg.id !== 'thinking'));
    }
    return () => clearInterval(intervalId);
  }, [thinking]);

  const isValidInput = (input) => input.trim().length > 0;
  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const fetchBotResponse = async (userMessage) => {
    setThinking(true);

    const apiUrl = `https://myapim-we.azure-api.net/smartlogics-bottie/chat?Apikey=b84b09caf9b644b6b77cce4c8ab38804&Name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&prompt=${encodeURIComponent(userMessage)}`;

    try {
      const response = await fetch(apiUrl);
      if (!response.ok) throw new Error(`API-Anfrage fehlgeschlagen: ${response.statusText}`);

      let data = await response.text();
      setThinking(false);

      if (data.includes('/(ENDE)\\')) {
        data = data.replace('/(ENDE)\\', '');
        setChatEnded(true);
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: data, sender: 'bot' },
          { text: "\n\nChat beendet. Du kannst jederzeit zurückkommen.", sender: 'bot', isEndMessage: true }
        ]);
      } else {
        setMessages((prevMessages) => [...prevMessages, { text: data, sender: 'bot' }]);
      }
    } catch (error) {
      console.error('Fehler beim Abrufen der Bot-Antwort:', error);
      setThinking(false);
      setMessages((prevMessages) => [...prevMessages, { text: `Fehler: ${error.message}`, sender: 'bot' }]);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!isValidInput(input) || chatEnded) return;

    setMessages(messages => [...messages, { text: input, sender: 'user' }]);
    setInput('');

    await fetchBotResponse(input);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !chatEnded) {
      e.preventDefault();
      sendMessage(e);
    }
  };

  const submitName = (e) => {
    e.preventDefault();
    if (isValidInput(name) && isValidEmail(email)) {
      setNameSubmitted(true);
    } else {
      alert('Bitte gib einen gültigen Namen und E-Mail ein.');
    }
  };

  if (!nameSubmitted) {
    return (
      <Box sx={{ maxWidth: 500, margin: 'auto', p: 2 }}>
        <Typography variant="h5" gutterBottom>Bitte gib deinen Namen und deine E-Mail ein</Typography>
        <form onSubmit={submitName}>
          <TextField fullWidth margin="normal" variant="outlined" value={name}           onChange={(e) => setName(e.target.value)} placeholder="Dein Name..." />
          <TextField fullWidth margin="normal" variant="outlined" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Deine E-Mail..." type="email" />
          <Button type="submit" variant="contained" color="primary" sx={{ mt: 2 }}>Weiter</Button>
        </form>
      </Box>
    );
  }

  return (
    <>
      <Box className="chat-container" sx={{ display: 'flex', flexDirection: 'column', maxHeight: 'calc(100vh - 120px)', overflowY: 'auto' }}>
        <Typography variant="h4" gutterBottom>Chatbot</Typography>
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          {messages.map((msg, index) => (
            <Box key={index} sx={{ display: 'flex', flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row', alignItems: 'center', mb: 2 }}>
              <Avatar sx={{ bgcolor: msg.sender === 'user' ? '#1976d2' : '#757575', ml: 1, mr: 1 }}>
                {msg.sender === 'user' ? name.toUpperCase().substring(0, 2) : 'BO'}
              </Avatar>
              <Typography
                component="span"
                sx={{
                  p: 1,
                  bgcolor: msg.sender === 'user' ? '#1976d2' : '#f0f0f0',
                  color: msg.sender === 'user' ? 'white' : 'black',
                  borderRadius: '10px',
                  maxWidth: '70%',
                  wordWrap: 'break-word',
                  fontStyle: msg.isEndMessage ? 'italic' : 'normal'
                }}
              >
                {msg.text}
              </Typography>
            </Box>
          ))}
          <div ref={endOfMessagesRef} />
        </Box>
        <Box className="input-area" component="form" onSubmit={sendMessage} sx={{ mt: 2 }}>
          <TextField
            fullWidth
            variant="outlined"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={chatEnded ? "" : "Nachricht eingeben..."} // Entferne den Platzhalter, wenn der Chat beendet ist
            multiline
            minRows={1}
            maxRows={5}
            sx={{ borderRadius: '20px' }}
            disabled={chatEnded} //Eingabefeld deaktivieren, wenn Chat beendet
            autoFocus={!chatEnded}
          />
          <Button type="submit" disabled={chatEnded} sx={{ ml: 1, borderRadius: '20px' }}>Senden</Button>
        </Box>
      </Box>
      <Typography sx={{ mt: 4, textAlign: 'center', color: 'gray' }}>
        <Link href="https://github.com/TechPrototyper/Chatbotdemo" target="_blank" rel="noopener noreferrer" sx={{ textDecoration: 'none', color: 'gray' }}>
          Arbeitsprobe, Bewerbung von Tim Walter für ein Projekt bei GULP. Hier klicken, um zum Github-Repo zu gelangen.
        </Link>
      </Typography>
    </>
  );
}

export default Chatbot;
