# Guide Création App Mobile Trimedh

## 🚀 Étape 1 : Créer le projet Flutter

```bash
# Créer le projet
flutter create trimedh_mobile
cd trimedh_mobile

# Ajouter les dépendances
flutter pub add http shared_preferences provider intl
```

## 📱 Étape 2 : Structure du projet

```
lib/
├── main.dart
├── config/
│   └── api_config.dart
├── services/
│   ├── api_service.dart
│   └── auth_service.dart
├── models/
│   ├── user.dart
│   ├── consultation.dart
│   └── patient.dart
├── screens/
│   ├── login_screen.dart
│   ├── home_screen.dart
│   ├── consultations_screen.dart
│   └── patients_screen.dart
└── widgets/
    ├── custom_button.dart
    └── loading_widget.dart
```

## 🔧 Étape 3 : Configuration réseau

### Trouver l'IP de votre PC
```bash
# Windows
ipconfig

# Cherchez "Adresse IPv4" de votre carte réseau
# Exemple: 192.168.1.100
```

### Configuration API
```dart
// lib/config/api_config.dart
class ApiConfig {
  // Remplacez par l'IP de votre PC
  static const String baseUrl = 'http://192.168.1.100:8000';
  
  // Pour émulateur Android
  // static const String baseUrl = 'http://10.0.2.2:8000';
}
```

## 📋 Étape 4 : Fichiers principaux

### 1. Service API
```dart
// lib/services/api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class ApiService {
  static String? _token;

  static void setToken(String token) {
    _token = token;
  }

  static Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  // Connexion
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/api/comptes/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      setToken(data['access']);
      return data;
    } else {
      throw Exception('Erreur de connexion');
    }
  }

  // Test de santé
  static Future<bool> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/health/'),
        headers: _headers,
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // Consultations
  static Future<List<Map<String, dynamic>>> getConsultations() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/medical/consultations/'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return List<Map<String, dynamic>>.from(data['results'] ?? data);
    } else {
      throw Exception('Erreur lors du chargement');
    }
  }
}
```

### 2. Écran de connexion
```dart
// lib/screens/login_screen.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _testConnection();
  }

  Future<void> _testConnection() async {
    final isHealthy = await ApiService.healthCheck();
    if (!isHealthy) {
      setState(() {
        _errorMessage = 'Impossible de se connecter au serveur';
      });
    }
  }

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final result = await ApiService.login(
        _emailController.text,
        _passwordController.text,
      );

      Navigator.pushReplacementNamed(context, '/home');
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Trimedh - Connexion'),
        backgroundColor: Colors.blue,
      ),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.local_hospital,
              size: 80,
              color: Colors.blue,
            ),
            SizedBox(height: 32),
            TextField(
              controller: _emailController,
              decoration: InputDecoration(
                labelText: 'Email',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.email),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(
                labelText: 'Mot de passe',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lock),
              ),
              obscureText: true,
            ),
            SizedBox(height: 24),
            if (_errorMessage != null)
              Container(
                padding: EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red[100],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _errorMessage!,
                  style: TextStyle(color: Colors.red),
                ),
              ),
            SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _login,
                child: _isLoading
                    ? CircularProgressIndicator(color: Colors.white)
                    : Text('Se connecter'),
              ),
            ),
            SizedBox(height: 16),
            Text(
              'Données de test:\nEmail: test@example.com\nMot de passe: password123',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
```

### 3. Écran d'accueil
```dart
// lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>> consultations = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadConsultations();
  }

  Future<void> _loadConsultations() async {
    try {
      final data = await ApiService.getConsultations();
      setState(() {
        consultations = data.take(5).toList(); // 5 dernières
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Trimedh - Accueil'),
        backgroundColor: Colors.blue,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tableau de bord',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatCard('Consultations', '${consultations.length}', Icons.medical_services),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: _buildStatCard('Patients', '0', Icons.people),
                ),
              ],
            ),
            SizedBox(height: 24),
            Text(
              'Dernières consultations',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            if (isLoading)
              Center(child: CircularProgressIndicator())
            else if (consultations.isEmpty)
              Center(child: Text('Aucune consultation'))
            else
              ...consultations.map((consultation) => _buildConsultationCard(consultation)),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        items: [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Accueil'),
          BottomNavigationBarItem(icon: Icon(Icons.medical_services), label: 'Consultations'),
          BottomNavigationBarItem(icon: Icon(Icons.people), label: 'Patients'),
        ],
        onTap: (index) {
          if (index == 1) {
            Navigator.pushNamed(context, '/consultations');
          }
        },
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, size: 32, color: Colors.blue),
            SizedBox(height: 8),
            Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            Text(title),
          ],
        ),
      ),
    );
  }

  Widget _buildConsultationCard(Map<String, dynamic> consultation) {
    return Card(
      margin: EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(Icons.medical_services, color: Colors.blue),
        title: Text(consultation['motif'] ?? 'Consultation'),
        subtitle: Text('Date: ${consultation['date_consultation']}'),
        trailing: Icon(Icons.arrow_forward_ios),
      ),
    );
  }
}
```

### 4. Application principale
```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(TrimedhApp());
}

class TrimedhApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Trimedh',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => LoginScreen(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}
```

## 🔧 Étape 5 : Configuration réseau

### 1. Démarrer le backend
```bash
cd trimed_backend
python manage.py runserver 0.0.0.0:8000
```

### 2. Trouver l'IP de votre PC
```bash
ipconfig
# Notez l'adresse IPv4 (ex: 192.168.1.100)
```

### 3. Modifier la configuration Flutter
```dart
// Dans lib/config/api_config.dart
static const String baseUrl = 'http://192.168.1.100:8000'; // Votre IP
```

## 📱 Étape 6 : Tester sur téléphone

### 1. Connecter le téléphone
```bash
# Activer le débogage USB sur Android
# Connecter via USB

# Vérifier la connexion
flutter devices
```

### 2. Lancer l'application
```bash
cd trimedh_mobile
flutter run
```

### 3. Tester la connexion
- Email: `test@example.com`
- Mot de passe: `password123`

## 🔥 Étape 7 : Build APK (optionnel)

```bash
# Créer l'APK
flutter build apk --release

# L'APK sera dans build/app/outputs/flutter-apk/
```

Votre application mobile Trimedh est prête ! 🎉